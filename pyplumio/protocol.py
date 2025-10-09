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
from pyplumio.helpers.event_manager import Event, EventManager
from pyplumio.stream import FrameReader, FrameWriter
from pyplumio.structures.network_info import (
    EthernetParameters,
    NetworkInfo,
    WirelessParameters,
)
from pyplumio.structures.regulator_data import ATTR_REGDATA

_LOGGER = logging.getLogger(__name__)

ConnectionLostCallback: TypeAlias = Callable[[], Awaitable[None]]


class Protocol(ABC):
    """Represents a protocol."""

    connected: asyncio.Event
    reader: FrameReader | None
    writer: FrameWriter | None
    _on_connection_lost: set[ConnectionLostCallback]

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
    def on_connection_lost(self) -> set[ConnectionLostCallback]:
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
    first_seen: datetime = field(default_factory=datetime.now)

    #: Datetime object representing time when device was last seen
    last_seen: datetime = field(default_factory=datetime.now)

    def __hash__(self) -> int:
        """Return a hash of the statistics based on unique address."""
        return self.address

    async def update_last_seen(
        self, data: Any = None, event: Event | None = None
    ) -> None:
        """Update last seen property."""
        self.last_seen = datetime.now()


class AsyncProtocol(Protocol, EventManager[PhysicalDevice]):
    """Represents an async protocol.

    This protocol implements frame handling using a single task and
    write queue.

    The frame handler processes frames in both directions:
    - Sends frames from the write queue to the device via frame writer
    - Reads incoming frames via frame reader and processes them

    Each received frame is passed to appropriate device handler for
    further processing.
    """

    _network_info: NetworkInfo
    _write_queue: asyncio.Queue[Frame]
    _statistics: Statistics

    def __init__(
        self,
        ethernet_parameters: EthernetParameters | None = None,
        wireless_parameters: WirelessParameters | None = None,
    ) -> None:
        """Initialize a new async protocol."""
        super().__init__()
        self._network_info = NetworkInfo(
            ethernet=ethernet_parameters or EthernetParameters(status=False),
            wireless=wireless_parameters or WirelessParameters(status=False),
        )
        self._write_queue = asyncio.Queue()
        self._statistics = Statistics()

    def connection_established(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Start frame producer and consumers."""
        self.reader = FrameReader(reader)
        self.writer = FrameWriter(writer)
        self._write_queue.put_nowait(StartMasterRequest(recipient=DeviceType.ECOMAX))
        self.create_task(
            self.frame_handler(reader=self.reader, writer=self.writer),
            name="frame_handler_task",
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
        self.cancel_tasks()
        await self.wait_until_done()
        if self.connected.is_set():
            await self._connection_close()
            await asyncio.gather(*(device.shutdown() for device in self.data.values()))

    async def frame_handler(self, reader: FrameReader, writer: FrameWriter) -> None:
        """Handle frame reads and writes."""
        await self.connected.wait()
        while self.connected.is_set():
            try:
                # Handle pending writes.
                frame: Frame | None
                if not self._write_queue.empty():
                    frame = await self._write_queue.get()
                    await writer.write(frame)
                    self._write_queue.task_done()
                    self.statistics.update_sent(frame)

                # Read and process frame.
                if frame := await reader.read():
                    self.statistics.update_received(frame)
                    device = await self._get_device_entry(frame.sender)
                    device.handle_frame(frame)

            except ProtocolError as e:
                self.statistics.failed_frames += 1
                _LOGGER.debug("Can't process received frame: %s", e)
            except (OSError, asyncio.TimeoutError):
                self.statistics.update_connection_lost()
                self.create_task(self.connection_lost())
                break
            except Exception:
                _LOGGER.exception("Unexpected exception")

    @acache
    async def _get_device_entry(self, device_type: DeviceType) -> PhysicalDevice:
        """Return the device entry."""
        name = device_type.name.lower()
        device = await PhysicalDevice.create(
            device_type, write_queue=self._write_queue, network_info=self._network_info
        )
        device.dispatch_nowait(ATTR_CONNECTED, True)
        device.dispatch_nowait(ATTR_SETUP, True)
        await self.dispatch(name, device)
        self.statistics.update_devices(device)
        return device

    @property
    def statistics(self) -> Statistics:
        """Return the statistics."""
        return self._statistics

    @property
    def network_info(self) -> NetworkInfo:
        """Return the network info."""
        return self._network_info


__all__ = [
    "Protocol",
    "DummyProtocol",
    "AsyncProtocol",
    "Statistics",
    "ConnectionLostCallback",
]
