"""Contains protocol representation."""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import logging

from pyplumio.const import ATTR_CONNECTED, DeviceType
from pyplumio.devices import AddressableDevice
from pyplumio.exceptions import FrameError, ReadError, UnknownDeviceError
from pyplumio.frames import Frame
from pyplumio.frames.requests import StartMasterRequest
from pyplumio.helpers.event_manager import EventManager
from pyplumio.stream import FrameReader, FrameWriter
from pyplumio.structures.network_info import (
    EthernetParameters,
    NetworkInfo,
    WirelessParameters,
)

_LOGGER = logging.getLogger(__name__)


class Protocol(ABC):
    """Represents a protocol."""

    connected: asyncio.Event
    reader: FrameReader | None
    writer: FrameWriter | None
    _on_connection_lost: set[Callable[[], Awaitable[None]]]

    def __init__(self) -> None:
        """Initialize a new protocol."""
        super().__init__()
        self.connected = asyncio.Event()
        self.reader = None
        self.writer = None
        self._on_connection_lost = set()

    async def close_writer(self) -> None:
        """Ensure that writer is closed."""
        if self.writer:
            await self.writer.close()
            self.writer = None

    @property
    def on_connection_lost(self) -> set[Callable[[], Awaitable[None]]]:
        """Return the callbacks that'll be called on connection lost."""
        return self._on_connection_lost

    @abstractmethod
    def connection_established(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Do something on connection established."""

    @abstractmethod
    async def connection_lost(self) -> None:
        """Do something on connection lost."""

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the protocol."""


class DummyProtocol(Protocol):
    """Represents a dummy protocol.

    This protocol sets frame reader and writer as attributes, then
    sets connected event and does nothing.
    """

    def connection_established(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Set reader and writer attributes and set the connected event."""
        self.reader = FrameReader(reader)
        self.writer = FrameWriter(writer)
        self.connected.set()

    async def connection_lost(self) -> None:
        """Close writer and call connection lost callbacks."""
        if self.connected.is_set():
            self.connected.clear()
            await self.close_writer()
            for callback in self.on_connection_lost:
                await callback()

    async def shutdown(self) -> None:
        """Shutdown the protocol."""
        if self.connected.is_set():
            self.connected.clear()
            await self.close_writer()


@dataclass
class Queues:
    """Represents asyncio queues."""

    __slots__ = ("read", "write")

    read: asyncio.Queue
    write: asyncio.Queue

    async def join(self) -> None:
        """Wait for queues to finish."""
        await asyncio.gather(self.read.join(), self.write.join())


class AsyncProtocol(Protocol, EventManager):
    """Represents an async protocol.

    This protocol implements producer-consumers pattern using
    asyncio queues.

    The frame producer tries to read frames from the write queue.
    If any is available, it sends them to the device via frame writer.

    It then reads stream via frame reader and puts received frame
    into the read queue.

    Frame consumers read frames from the read queue, create device
    entry, if needed, and send frame to the entry for the processing.
    """

    consumers_count: int
    data: dict[str, AddressableDevice]
    _network: NetworkInfo
    _queues: Queues

    def __init__(
        self,
        ethernet_parameters: EthernetParameters | None = None,
        wireless_parameters: WirelessParameters | None = None,
        consumers_count: int = 3,
    ) -> None:
        """Initialize a new async protocol."""
        super().__init__()
        self.consumers_count = consumers_count
        self._network = NetworkInfo(
            eth=ethernet_parameters or EthernetParameters(status=False),
            wlan=wireless_parameters or WirelessParameters(status=False),
        )
        self._queues = Queues(read=asyncio.Queue(), write=asyncio.Queue())

    def connection_established(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Start frame producer and consumers."""
        self.reader = FrameReader(reader)
        self.writer = FrameWriter(writer)
        self._queues.write.put_nowait(StartMasterRequest(recipient=DeviceType.ECOMAX))
        self.create_task(
            self.frame_producer(self._queues, reader=self.reader, writer=self.writer)
        )
        for _ in range(self.consumers_count):
            self.create_task(self.frame_consumer(self._queues.read))

        for device in self.data.values():
            device.dispatch_nowait(ATTR_CONNECTED, True)

        self.connected.set()

    async def _connection_close(self) -> None:
        """Close the connection if it is established."""
        self.connected.clear()
        await asyncio.gather(
            *[device.dispatch(ATTR_CONNECTED, False) for device in self.data.values()]
        )
        await self.close_writer()

    async def connection_lost(self) -> None:
        """Close the connection and call connection lost callbacks."""
        if self.connected.is_set():
            await self._connection_close()
            await asyncio.gather(*[callback() for callback in self.on_connection_lost])

    async def shutdown(self) -> None:
        """Shutdown the protocol and close the connection."""
        await self._queues.join()
        self.cancel_tasks()
        await self.wait_until_done()
        if self.connected.is_set():
            await self._connection_close()
            await asyncio.gather(*[device.shutdown() for device in self.data.values()])

    async def frame_producer(
        self, queues: Queues, reader: FrameReader, writer: FrameWriter
    ) -> None:
        """Handle frame reads and writes."""
        await self.connected.wait()
        while self.connected.is_set():
            try:
                if not queues.write.empty():
                    await writer.write(await queues.write.get())
                    queues.write.task_done()

                if (response := await reader.read()) is not None:
                    queues.read.put_nowait(response)

            except (ReadError, UnknownDeviceError, FrameError) as e:
                _LOGGER.debug("Can't process received frame: %s", e)
            except (OSError, asyncio.TimeoutError):
                self.create_task(self.connection_lost())
                break
            except Exception:
                _LOGGER.exception("Unexpected exception")

    async def frame_consumer(self, queue: asyncio.Queue) -> None:
        """Handle frame processing."""
        await self.connected.wait()
        while self.connected.is_set():
            frame: Frame = await queue.get()
            device = await self.get_device_entry(frame.sender)
            device.handle_frame(frame)
            queue.task_done()

    async def get_device_entry(self, device_type: DeviceType) -> AddressableDevice:
        """Set up or return a device entry."""
        name = device_type.name.lower()
        if name not in self.data:
            device = await AddressableDevice.create(
                device_type, queue=self._queues.write, network=self._network
            )
            device.dispatch_nowait(ATTR_CONNECTED, True)
            self.create_task(device.async_setup())
            self.set_event(name)
            self.data[name] = device

        return self.data[name]
