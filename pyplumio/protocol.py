"""Contains protocol representation."""
from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, Dict, Final, Optional, Tuple

from pyplumio.const import ATTR_LOADED, DeviceType, FrameType
from pyplumio.devices import Addressable, get_device_handler
from pyplumio.exceptions import (
    FrameError,
    ReadError,
    UnknownDeviceError,
    UnknownFrameError,
)
from pyplumio.frames.requests import StartMasterRequest
from pyplumio.helpers.factory import factory
from pyplumio.helpers.network_info import (
    EthernetParameters,
    NetworkInfo,
    WirelessParameters,
)
from pyplumio.helpers.task_manager import TaskManager
from pyplumio.stream import FrameReader, FrameWriter
from pyplumio.structures.network_info import ATTR_NETWORK

_LOGGER = logging.getLogger(__name__)

CONSUMERS_NUMBER: Final = 2


def _get_device_handler_and_name(address: int) -> Tuple[str, str]:
    """Get device handler full path and lowercased class name."""
    handler = get_device_handler(address)
    _, class_name = handler.rsplit(".", 1)
    return handler, class_name.lower()


class Protocol(TaskManager):
    """Represents protocol."""

    writer: Optional[FrameWriter]
    reader: Optional[FrameReader]
    devices: Dict[str, Addressable]
    connected: asyncio.Event
    _network: NetworkInfo
    _queues: Tuple[asyncio.Queue, asyncio.Queue]
    _connection_lost_callback: Optional[Callable[[], Awaitable[None]]]

    def __init__(
        self,
        connection_lost_callback: Optional[Callable[[], Awaitable[None]]] = None,
        ethernet_parameters: Optional[EthernetParameters] = None,
        wireless_parameters: Optional[WirelessParameters] = None,
    ):
        """Initialize new Protocol object."""
        super().__init__()
        self.writer = None
        self.reader = None
        self.devices = {}
        self.connected = asyncio.Event()
        read_queue: asyncio.Queue = asyncio.Queue()
        write_queue: asyncio.Queue = asyncio.Queue()
        self._queues = (read_queue, write_queue)
        self._connection_lost_callback = connection_lost_callback
        if ethernet_parameters is None:
            ethernet_parameters = EthernetParameters()

        if wireless_parameters is None:
            wireless_parameters = WirelessParameters()

        self._network = NetworkInfo(eth=ethernet_parameters, wlan=wireless_parameters)

    def __getattr__(self, name: str):
        """Return attributes from the underlying devices table."""
        if name in self.devices:
            return self.devices[name]

        raise AttributeError

    async def frame_producer(
        self, read_queue: asyncio.Queue, write_queue: asyncio.Queue
    ) -> None:
        """Handle frame reads."""
        await self.connected.wait()
        while self.connected.is_set():
            try:
                if write_queue.qsize() > 0:
                    request = await write_queue.get()
                    await self.writer.write(request)
                    write_queue.task_done()

                response = await self.reader.read()
                if response is not None:
                    read_queue.put_nowait(response)
            except UnknownFrameError as e:
                _LOGGER.debug("Unknown frame type: %s", e)
            except ReadError as e:
                _LOGGER.debug("Read error: %s", e)
            except FrameError as e:
                _LOGGER.warning("Can't process received frame: %s", e)
            except (OSError, asyncio.TimeoutError):
                self.create_task(self.connection_lost())
                break
            except Exception as e:  # pylint: disable=broad-except
                _LOGGER.exception(e)

    async def frame_consumer(
        self, read_queue: asyncio.Queue, write_queue: asyncio.Queue
    ) -> None:
        """Handle frame processing."""
        await self.connected.wait()
        while self.connected.is_set():
            frame = await read_queue.get()
            try:
                handler, name = _get_device_handler_and_name(frame.sender)
            except UnknownDeviceError as e:
                _LOGGER.debug("Unknown device: %s", e)
                read_queue.task_done()
                continue

            if name not in self.devices:
                device: Addressable = factory(handler, queue=write_queue)
                device.set_device_data(ATTR_LOADED, True)
                self.devices[name] = device
                self.set_event(name)

            self.devices[name].handle_frame(frame)

            if frame.frame_type in (
                FrameType.REQUEST_CHECK_DEVICE,
                FrameType.REQUEST_PROGRAM_VERSION,
            ):
                write_queue.put_nowait(
                    frame.response(data={ATTR_NETWORK: self._network})
                )

            read_queue.task_done()

    def connection_established(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        """Start consumers and producer tasks."""
        self.reader = FrameReader(reader)
        self.writer = FrameWriter(writer)
        write_queue = self.queues[1]
        write_queue.put_nowait(StartMasterRequest(recipient=DeviceType.ECOMAX))
        self.create_task(self.frame_producer(*self.queues))
        for _ in range(CONSUMERS_NUMBER):
            self.create_task(self.frame_consumer(*self.queues))

        self.connected.set()

    async def connection_lost(self):
        """Shutdown consumers and call connection lost callback."""
        if self.connected.is_set():
            self.connected.clear()
            if self._connection_lost_callback is not None:
                await self._connection_lost_callback()

    async def shutdown(self):
        """Shutdown protocol tasks."""
        await asyncio.gather(*[queue.join() for queue in self.queues])
        self.cancel_tasks()
        await self.wait_until_done()
        for device in self.devices.values():
            await device.shutdown()

        if self.writer:
            await self.writer.close()

    async def get_device(
        self, device: str, timeout: Optional[float] = None
    ) -> Addressable:
        """Wait for device and return it once it's available."""
        if device not in self.devices:
            await asyncio.wait_for(self.create_event(device).wait(), timeout=timeout)

        return self.devices[device]

    @property
    def queues(self) -> Tuple[asyncio.Queue, asyncio.Queue]:
        """Return protocol queues."""
        return self._queues
