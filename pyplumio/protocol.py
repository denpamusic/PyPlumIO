"""Contains protocol representation."""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
import logging
from typing import Any, Final, Literal, TypeAlias

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


@dataclass(slots=True)
class Queues:
    """Represents asyncio queues."""

    read: asyncio.Queue[Frame]
    write: asyncio.Queue[Frame]

    async def join(self) -> None:
        """Wait for queues to finish."""
        await asyncio.gather(self.read.join(), self.write.join())


NEVER: Final = "never"


@dataclass(slots=True, kw_only=True)
class Statistics:
    """Represents a connection statistics."""

    #: Number of received bytes. Resets on reconnect.
    received_bytes: int = 0

    #: Number of received frames. Resets on reconnect.
    received_frames: int = 0

    #: Number of sent bytes. Resets on reconnect.
    sent_bytes: int = 0

    #: Number of sent frames. Resets on reconnect.
    sent_frames: int = 0

    #: Number of failed frames. Resets on reconnect.
    failed_frames: int = 0

    #: Datetime object representing connection time
    connected_since: datetime | Literal["never"] = NEVER

    #: Datetime object representing last connection loss event
    connection_loss_at: datetime | Literal["never"] = NEVER

    #: Number of connection lost event
    connection_losses: int = 0

    #: List of statistics for connected devices
    devices: set[DeviceStatistics] = field(default_factory=set)

    def update_sent(self, frame: Frame) -> None:
        """Update sent frames statistics."""
        self.sent_bytes += frame.length
        self.sent_frames += 1

    def update_received(self, frame: Frame) -> None:
        """Update received frames statistics."""
        self.received_bytes += frame.length
        self.received_frames += 1

    def update_connection_lost(self) -> None:
        """Update connection lost counter."""
        self.connection_losses += 1
        self.connection_loss_at = datetime.now()

    def update_devices(self, device: PhysicalDevice) -> None:
        """Update connected devices."""
        device_statistics = DeviceStatistics(address=device.address)
        device.subscribe(ATTR_REGDATA, device_statistics.update_last_seen)
        self.devices.add(device_statistics)

    def reset_transfer_statistics(self) -> None:
        """Reset transfer statistics."""
        self.sent_bytes = 0
        self.sent_frames = 0
        self.received_bytes = 0
        self.received_frames = 0
        self.failed_frames = 0


@dataclass(slots=True, kw_only=True)
class DeviceStatistics:
    """Represents a device statistics."""

    #: Device address
    address: int

    #: Datetime object representing connection time
    connected_since: datetime = field(default_factory=datetime.now)

    #: Datetime object representing time when device was last seen
    last_seen: datetime = field(default_factory=datetime.now)

    def __hash__(self) -> int:
        """Return a hash of the statistics based on unique address."""
        return self.address

    async def update_last_seen(self, _: Any) -> None:
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
        for consumer_id in range(self.consumers_count):
            self.create_task(
                self.frame_consumer(self._queues.read),
                name=f"frame_consumer_task ({consumer_id})",
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

    async def _write_from_queue(
        self, writer: FrameWriter, queue: asyncio.Queue[Frame]
    ) -> None:
        """Send frame from the queue to the remote device."""
        frame = await queue.get()
        await writer.write(frame)
        queue.task_done()
        self.statistics.update_sent(frame)

    async def _read_into_queue(
        self, reader: FrameReader, queue: asyncio.Queue[Frame]
    ) -> None:
        """Read frame from the remote device into the queue."""
        if frame := await reader.read():
            queue.put_nowait(frame)
            self.statistics.update_received(frame)

    async def frame_producer(
        self, queues: Queues, reader: FrameReader, writer: FrameWriter
    ) -> None:
        """Handle frame reads and writes."""
        await self.connected.wait()
        while self.connected.is_set():
            try:
                if not queues.write.empty():
                    await self._write_from_queue(writer, queues.write)

                await self._read_into_queue(reader, queues.read)
            except ProtocolError as e:
                self.statistics.failed_frames += 1
                _LOGGER.debug("Can't process received frame: %s", e)
            except (OSError, asyncio.TimeoutError):
                self.statistics.update_connection_lost()
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
                self.statistics.update_devices(device)

        return self.data[name]

    @property
    def statistics(self) -> Statistics:
        """Return the statistics."""
        return self._statistics


__all__ = ["Protocol", "DummyProtocol", "AsyncProtocol", "Statistics"]
