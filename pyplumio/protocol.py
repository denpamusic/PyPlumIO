"""Contains protocol representation."""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
import logging
from typing import Any, Final, Literal

from dataslots import dataslots
from typing_extensions import TypeAlias

from pyplumio.const import ATTR_CONNECTED, ATTR_SETUP, DeviceType
from pyplumio.devices import PhysicalDevice
from pyplumio.exceptions import ProtocolError
from pyplumio.frames import Frame
from pyplumio.frames.requests import StartMasterRequest
from pyplumio.helpers.async_cache import acache
from pyplumio.helpers.event_manager import EventManager
from pyplumio.stream import FrameReader, FrameWriter
from pyplumio.structures.network_info import (
    EthernetParameters,
    NetworkInfo,
    WirelessParameters,
)
from pyplumio.structures.regulator_data import ATTR_REGDATA

_LOGGER = logging.getLogger(__name__)

Callback: TypeAlias = Callable[[], Awaitable[None]]


class Protocol(ABC):
    """Represents a protocol."""

    connected: asyncio.Event
    reader: FrameReader | None
    writer: FrameWriter | None
    _on_connection_lost: set[Callback]

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
    def on_connection_lost(self) -> set[Callback]:
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
            await asyncio.gather(*(callback() for callback in self.on_connection_lost))

    async def shutdown(self) -> None:
        """Shutdown the protocol."""
        if self.connected.is_set():
            self.connected.clear()
            await self.close_writer()


@dataclass
class Queues:
    """Represents asyncio queues."""

    __slots__ = ("read", "write")

    read: asyncio.Queue[Frame]
    write: asyncio.Queue[Frame]

    async def join(self) -> None:
        """Wait for queues to finish."""
        await asyncio.gather(self.read.join(), self.write.join())


NEVER: Final = "never"


@dataslots
@dataclass
class Statistics:
    """Represents a connection statistics."""

    received_bytes: int = 0
    received_frames: int = 0
    sent_bytes: int = 0
    sent_frames: int = 0
    failed_frames: int = 0
    connected_since: datetime | Literal["never"] = NEVER
    connection_loss_at: datetime | Literal["never"] = NEVER
    connection_losses: int = 0
    devices: list[DeviceStatistics] = field(default_factory=list)

    def update_transfer_statistics(
        self, sent: Frame | None = None, received: Frame | None = None
    ) -> None:
        """Update transfer statistics."""
        if sent:
            self.sent_bytes += sent.length
            self.sent_frames += 1

        if received:
            self.received_bytes += received.length
            self.received_frames += 1

    def reset_transfer_statistics(self) -> None:
        """Reset transfer statistics."""
        self.sent_bytes = 0
        self.sent_frames = 0
        self.received_bytes = 0
        self.received_frames = 0
        self.failed_frames = 0


@dataslots
@dataclass
class DeviceStatistics:
    """Represents a device statistics."""

    name: str
    connected_since: datetime | Literal["never"] = NEVER
    last_seen: datetime | Literal["never"] = NEVER

    async def update_last_seen(self, data: Any) -> None:
        """Update last seen property."""
        self.last_seen = datetime.now()


class AsyncProtocol(Protocol, EventManager[PhysicalDevice]):
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
    _network: NetworkInfo
    _queues: Queues
    _entry_lock: asyncio.Lock
    _statistics: Statistics

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
        self._entry_lock = asyncio.Lock()
        self._statistics = Statistics()

    def connection_established(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Start frame producer and consumers."""
        self.reader = FrameReader(reader)
        self.writer = FrameWriter(writer)
        self._queues.write.put_nowait(StartMasterRequest(recipient=DeviceType.ECOMAX))
        self.create_task(
            self.frame_producer(self._queues, reader=self.reader, writer=self.writer),
            name="frame_producer_task",
        )
        for consumer in range(self.consumers_count):
            self.create_task(
                self.frame_consumer(self._queues.read),
                name=f"frame_consumer_task ({consumer})",
            )

        for device in self.data.values():
            device.dispatch_nowait(ATTR_CONNECTED, True)

        self.connected.set()
        self.statistics.reset_transfer_statistics()
        self.statistics.connected_since = datetime.now()

    async def _connection_close(self) -> None:
        """Close the connection if it is established."""
        self.connected.clear()
        await asyncio.gather(
            *(device.dispatch(ATTR_CONNECTED, False) for device in self.data.values())
        )
        await self.close_writer()

    async def connection_lost(self) -> None:
        """Close the connection and call connection lost callbacks."""
        if self.connected.is_set():
            await self._connection_close()
            await asyncio.gather(*(callback() for callback in self.on_connection_lost))

    async def shutdown(self) -> None:
        """Shutdown the protocol and close the connection."""
        await self._queues.join()
        self.cancel_tasks()
        await self.wait_until_done()
        if self.connected.is_set():
            await self._connection_close()
            await asyncio.gather(*(device.shutdown() for device in self.data.values()))

    async def frame_producer(
        self, queues: Queues, reader: FrameReader, writer: FrameWriter
    ) -> None:
        """Handle frame reads and writes."""
        statistics = self.statistics
        await self.connected.wait()
        while self.connected.is_set():
            try:
                request = None
                if not queues.write.empty():
                    request = await queues.write.get()
                    await writer.write(request)
                    queues.write.task_done()

                if response := await reader.read():
                    queues.read.put_nowait(response)

                statistics.update_transfer_statistics(request, response)

            except ProtocolError as e:
                statistics.failed_frames += 1
                _LOGGER.debug("Can't process received frame: %s", e)
            except (OSError, asyncio.TimeoutError):
                statistics.connection_losses += 1
                statistics.connection_loss_at = datetime.now()
                self.create_task(self.connection_lost())
                break
            except Exception:
                _LOGGER.exception("Unexpected exception")

    async def frame_consumer(self, queue: asyncio.Queue[Frame]) -> None:
        """Handle frame processing."""
        await self.connected.wait()
        while self.connected.is_set():
            frame = await queue.get()
            device = await self.get_device_entry(frame.sender)
            device.handle_frame(frame)
            queue.task_done()

    @acache
    async def get_device_entry(self, device_type: DeviceType) -> PhysicalDevice:
        """Return the device entry."""
        name = device_type.name.lower()
        async with self._entry_lock:
            if name not in self.data:
                device = await PhysicalDevice.create(
                    device_type, queue=self._queues.write, network=self._network
                )
                device.dispatch_nowait(ATTR_CONNECTED, True)
                device.dispatch_nowait(ATTR_SETUP, True)
                await self.dispatch(name, device)
                self.statistics.devices.append(
                    device_statistics := DeviceStatistics(
                        name=name,
                        connected_since=datetime.now(),
                        last_seen=datetime.now(),
                    )
                )
                device.subscribe(ATTR_REGDATA, device_statistics.update_last_seen)

        return self.data[name]

    @property
    def statistics(self) -> Statistics:
        """Return the statistics."""
        return self._statistics


__all__ = ["Protocol", "DummyProtocol", "AsyncProtocol", "Statistics"]
