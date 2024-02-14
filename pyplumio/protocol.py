"""Contains protocol representation."""
from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from collections.abc import Awaitable, Callable
import logging
from typing import cast

from pyplumio.const import ATTR_CONNECTED, DeviceType
from pyplumio.devices import AddressableDevice, get_device_handler_and_name
from pyplumio.exceptions import (
    FrameDataError,
    FrameError,
    ReadError,
    UnknownDeviceError,
)
from pyplumio.frames import Frame
from pyplumio.frames.requests import StartMasterRequest
from pyplumio.helpers.event_manager import EventManager
from pyplumio.helpers.factory import factory
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


class AsyncProtocol(Protocol, EventManager):
    """Represents an async protocol.

    This protocol implements producer-consumers pattern using
    asyncio queues.

    The frame producer tries to read frames from write queue, if any
    available, and sends them to the device via frame writer.

    It reads stream via frame reader, creates device handler entry
    and puts received frame and handler into the read queue.

    Frame consumers reads handler-frame tuples from the read queue and
    sends frame to respective handler for further processing.
    """

    consumers_number: int
    _network: NetworkInfo
    _queues: tuple[asyncio.Queue, asyncio.Queue]

    def __init__(
        self,
        ethernet_parameters: EthernetParameters | None = None,
        wireless_parameters: WirelessParameters | None = None,
        consumers_number: int = 3,
    ) -> None:
        """Initialize a new async protocol."""
        super().__init__()
        self.consumers_number = consumers_number
        self._network = NetworkInfo(
            eth=(
                EthernetParameters(status=False)
                if ethernet_parameters is None
                else ethernet_parameters
            ),
            wlan=(
                WirelessParameters(status=False)
                if wireless_parameters is None
                else wireless_parameters
            ),
        )
        self._queues = (asyncio.Queue(), asyncio.Queue())

    def connection_established(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Start frame producer and consumers."""
        self.reader = FrameReader(reader)
        self.writer = FrameWriter(writer)
        read_queue, write_queue = self.queues
        write_queue.put_nowait(StartMasterRequest(recipient=DeviceType.ECOMAX))
        self.create_task(self.frame_producer(*self.queues))
        for _ in range(self.consumers_number):
            self.create_task(self.frame_consumer(read_queue))

        for device in self.data.values():
            device.dispatch_nowait(ATTR_CONNECTED, True)

        self.connected.set()

    async def connection_lost(self) -> None:
        """Close the writer and call connection lost callbacks."""
        if not self.connected.is_set():
            return

        self.connected.clear()
        for device in self.data.values():
            # Notify devices about connection loss.
            await device.dispatch(ATTR_CONNECTED, False)

        await self.close_writer()
        for callback in self.on_connection_lost:
            await callback()

    async def shutdown(self) -> None:
        """Shutdown protocol tasks."""
        await asyncio.gather(*[queue.join() for queue in self.queues])
        await super(Protocol, self).shutdown()
        for device in self.data.values():
            await device.shutdown()

        if self.connected.is_set():
            self.connected.clear()
            await self.close_writer()

    async def frame_producer(
        self, read_queue: asyncio.Queue, write_queue: asyncio.Queue
    ) -> None:
        """Handle frame reads and writes."""
        await self.connected.wait()
        reader = cast(FrameReader, self.reader)
        writer = cast(FrameWriter, self.writer)
        while self.connected.is_set():
            try:
                if write_queue.qsize() > 0:
                    await writer.write(await write_queue.get())
                    write_queue.task_done()

                if (response := await reader.read()) is not None:
                    read_queue.put_nowait(
                        (
                            self.setup_device_entry(cast(DeviceType, response.sender)),
                            response,
                        )
                    )

            except FrameDataError as e:
                _LOGGER.warning("Incorrect payload: %s", e)
            except ReadError as e:
                _LOGGER.debug("Read error: %s", e)
            except UnknownDeviceError as e:
                _LOGGER.debug("Unknown device: %s", e)
            except FrameError as e:
                _LOGGER.debug("Can't process received frame: %s", e)
            except (OSError, asyncio.TimeoutError):
                self.create_task(self.connection_lost())
                break
            except Exception as e:  # pylint: disable=broad-except
                _LOGGER.exception(e)

    async def frame_consumer(self, read_queue: asyncio.Queue) -> None:
        """Handle frame processing."""
        await self.connected.wait()
        while self.connected.is_set():
            device, frame = cast(
                tuple[AddressableDevice, Frame], await read_queue.get()
            )
            device.handle_frame(frame)
            read_queue.task_done()

    def setup_device_entry(self, device_type: DeviceType) -> AddressableDevice:
        """Set up device entry."""
        handler, name = get_device_handler_and_name(device_type)
        if name not in self.data:
            self._create_device_entry(name, handler)

        return cast(AddressableDevice, self.data[name])

    def _create_device_entry(self, name: str, handler: str) -> None:
        """Create device entry."""
        write_queue = self.queues[1]
        device: AddressableDevice = factory(
            handler, queue=write_queue, network=self._network
        )
        device.dispatch_nowait(ATTR_CONNECTED, True)
        self.create_task(device.async_setup())
        self.data[name] = device
        self.set_event(name)

    @property
    def queues(self) -> tuple[asyncio.Queue, asyncio.Queue]:
        """Return the protocol queues."""
        return self._queues
