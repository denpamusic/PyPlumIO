"""Contains protocol representation."""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Iterable
import logging
from typing import Any, Dict, Tuple

from pyplumio.const import DATA_NETWORK, ECOMAX_ADDRESS
from pyplumio.devices import Device, get_device_handler
from pyplumio.exceptions import (
    FrameError,
    ReadError,
    UnknownDeviceError,
    UnknownFrameError,
)
from pyplumio.frames.requests import CheckDevice, ProgramVersion, StartMaster
from pyplumio.helpers.factory import factory
from pyplumio.helpers.network_info import (
    DEFAULT_IP,
    DEFAULT_NETMASK,
    WLAN_ENCRYPTION_NONE,
    EthernetParameters,
    NetworkInfo,
    WirelessParameters,
)
from pyplumio.stream import FrameReader, FrameWriter

_LOGGER = logging.getLogger(__name__)


def _get_device_handler_and_name(address: int) -> Tuple[str, str]:
    """Get device handler full path and lowercased class name."""
    handler = get_device_handler(address)
    _, class_name = handler.rsplit(".", 1)
    return handler, class_name.lower()


class Protocol:
    """Represents protocol."""

    writer: FrameWriter
    reader: FrameReader
    devices: Dict[str, Device]
    _network: NetworkInfo
    _queues: Iterable[asyncio.Queue]
    _tasks: Iterable[asyncio.Task]
    _connection_lost_callback: Any

    def __init__(
        self,
        reader: FrameReader,
        writer: FrameWriter,
        connection_lost_callback: Callable[[], Awaitable[Any]],
    ):
        """Initialize new Protocol object."""
        self.writer = writer
        self.reader = reader
        self.devices = {}
        lock: asyncio.Lock = asyncio.Lock()
        read_queue: asyncio.Queue = asyncio.Queue()
        write_queue: asyncio.Queue = asyncio.Queue()
        write_queue.put_nowait(StartMaster(recipient=ECOMAX_ADDRESS))
        self._queues = (read_queue, write_queue)
        self._tasks = [
            asyncio.create_task(self.frame_consumer(*self._queues)) for _ in range(2)
        ]
        self._tasks.append(asyncio.create_task(self.frame_producer(read_queue, lock)))
        self._tasks.append(asyncio.create_task(self.write_consumer(write_queue, lock)))
        self._connection_lost_callback = connection_lost_callback
        self._network = NetworkInfo()

    async def frame_consumer(
        self, read_queue: asyncio.Queue, write_queue: asyncio.Queue
    ) -> None:
        """Handle frame processing."""
        while True:
            frame = await read_queue.get()
            try:
                handler, name = _get_device_handler_and_name(frame.sender)
                device: Device = (
                    self.devices[name]
                    if name in self.devices
                    else factory(handler, queue=write_queue)
                )
                await device.handle_frame(frame)
                if frame.is_type(CheckDevice, ProgramVersion):
                    write_queue.put_nowait(
                        frame.response(data={DATA_NETWORK: self._network})
                    )

                self.devices[name] = device

            except UnknownDeviceError as e:
                _LOGGER.debug("Device debug: %s", e)

            except UnknownFrameError as e:
                _LOGGER.debug("Frame debug: %s", e)

            read_queue.task_done()

    async def frame_producer(
        self, read_queue: asyncio.Queue, lock: asyncio.Lock
    ) -> None:
        """Handle frame reads."""
        while True:
            try:
                async with lock:
                    read_queue.put_nowait(await self.reader.read())
            except (UnknownFrameError, ReadError) as e:
                _LOGGER.debug("Read debug: %s", e)
            except FrameError as e:
                _LOGGER.warning("Frame warning: %s", e)
            except asyncio.TimeoutError:
                await self.shutdown()
                self._connection_lost_callback()

    async def write_consumer(
        self, write_queue: asyncio.Queue, lock: asyncio.Lock
    ) -> None:
        """Handle frame writes."""
        while True:
            frame = await write_queue.get()
            async with lock:
                await self.writer.write(frame)
            write_queue.task_done()

    async def shutdown(self):
        """Shutdown protocol tasks and handlers."""
        for queue in self._queues:
            await queue.join()

        for task in self._tasks:
            task.cancel()

        await asyncio.gather(*self._tasks, return_exceptions=True)
        await self.writer.close()

    async def wait_for_device(self, device: str) -> Device:
        """Wait for device and return it once it's available."""
        while device not in self.devices:
            await asyncio.sleep(1)

        return self.devices[device]

    def set_eth(
        self, ip: str, netmask: str = DEFAULT_NETMASK, gateway: str = DEFAULT_IP
    ) -> None:
        """Set ethernet info for sending to the devices. Used for
        informational purposes only."""
        self._network.eth = EthernetParameters(
            ip=ip, netmask=netmask, gateway=gateway, status=True
        )

    def set_wlan(
        self,
        ssid: str,
        ip: str,
        encryption: int = WLAN_ENCRYPTION_NONE,
        netmask: str = DEFAULT_NETMASK,
        gateway: str = DEFAULT_IP,
        quality: int = 100,
    ) -> None:
        """Set wireless info for sending to the devices. Used for
        informational purposes only."""
        self._network.wlan = WirelessParameters(
            ssid=ssid,
            encryption=encryption,
            quality=quality,
            ip=ip,
            netmask=netmask,
            gateway=gateway,
            status=True,
        )
