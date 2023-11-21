"""Contains protocol representation."""
from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from collections.abc import Awaitable, Callable
import logging
from typing import Final, cast

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

CONSUMERS_NUMBER: Final = 2


class Protocol(ABC):
    """Represents a protocol."""

    writer: FrameWriter | None
    reader: FrameReader | None
    connected: asyncio.Event
    _connection_lost_callback: Callable[[], Awaitable[None]] | None
    _network: NetworkInfo

    def __init__(
        self,
        connection_lost_callback: Callable[[], Awaitable[None]] | None = None,
        ethernet_parameters: EthernetParameters | None = None,
        wireless_parameters: WirelessParameters | None = None,
    ):
        """Initialize a new protocol."""
        super().__init__()
        self.writer = None
        self.reader = None
        self.connected = asyncio.Event()
        self._connection_lost_callback = connection_lost_callback
        if ethernet_parameters is None:
            ethernet_parameters = EthernetParameters(status=False)

        if wireless_parameters is None:
            wireless_parameters = WirelessParameters(status=False)

        self._network = NetworkInfo(eth=ethernet_parameters, wlan=wireless_parameters)

    async def close_writer(self) -> None:
        """Ensure that writer is closed."""
        if not self.writer:
            return

        try:
            await self.writer.close()
        except (OSError, asyncio.TimeoutError):
            # Ignore any connection errors when closing the writer.
            pass
        finally:
            self.writer = None

    @abstractmethod
    def connection_established(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        """Called when connection is established."""

    @abstractmethod
    async def connection_lost(self):
        """Called when connection is lost."""

    @abstractmethod
    async def shutdown(self):
        """Shutdown the protocol."""


class DummyProtocol(Protocol):
    """Represents a dummy protocol.

    This protocol sets frame reader and writer as attributes, then
    sets connected event and does nothing.
    """

    def connection_established(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        """Called when connection is established."""
        self.reader = FrameReader(reader)
        self.writer = FrameWriter(writer)
        self.connected.set()

    async def connection_lost(self):
        """Called when connection is lost."""
        if self.connected.is_set():
            self.connected.clear()
            await self.close_writer()
            if self._connection_lost_callback is not None:
                await self._connection_lost_callback()

    async def shutdown(self):
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

    _queues: tuple[asyncio.Queue, asyncio.Queue]

    def __init__(
        self,
        connection_lost_callback: Callable[[], Awaitable[None]] | None = None,
        ethernet_parameters: EthernetParameters | None = None,
        wireless_parameters: WirelessParameters | None = None,
    ):
        """Initialize a new default protocol."""
        super().__init__(
            connection_lost_callback, ethernet_parameters, wireless_parameters
        )
        self._queues = (asyncio.Queue(), asyncio.Queue())

    def connection_established(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        """Called when connection is established."""
        self.reader = FrameReader(reader)
        self.writer = FrameWriter(writer)
        read_queue, write_queue = self.queues
        write_queue.put_nowait(StartMasterRequest(recipient=DeviceType.ECOMAX))
        self.create_task(self.frame_producer(*self.queues))
        for _ in range(CONSUMERS_NUMBER):
            self.create_task(self.frame_consumer(read_queue))

        for device in self.data.values():
            device.dispatch_nowait(ATTR_CONNECTED, True)

        self.connected.set()

    async def connection_lost(self):
        """Called when connection is lost."""
        if self.connected.is_set():
            self.connected.clear()
            for device in self.data.values():
                # Notify devices about connection loss.
                await device.dispatch(ATTR_CONNECTED, False)

            await self.close_writer()
            if self._connection_lost_callback is not None:
                await self._connection_lost_callback()

    async def shutdown(self):
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
        while self.connected.is_set():
            try:
                if write_queue.qsize() > 0:
                    await self.writer.write(await write_queue.get())
                    write_queue.task_done()

                if (response := await self.reader.read()) is not None:
                    read_queue.put_nowait(
                        (self.setup_device_entry(response.sender), response)
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
        """Setup the device entry."""
        handler, name = get_device_handler_and_name(device_type)
        if name not in self.data:
            self._create_device_entry(name, handler)

        return self.data[name]

    def _create_device_entry(self, name: str, handler: str) -> None:
        """Create the device entry."""
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
        """Protocol queues."""
        return self._queues
