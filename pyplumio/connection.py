"""Contains main connection class."""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from collections.abc import Callable
import logging
import sys
from typing import Any, Awaitable, Dict, Final, Optional, Tuple

from serial import SerialException
import serial_asyncio

from . import requests, responses
from .constants import DATA_MIXERS, DEFAULT_IP, DEFAULT_NETMASK, WLAN_ENCRYPTION
from .devices import ECOMAX_ADDRESS, DevicesCollection
from .exceptions import FrameError, FrameTypeError
from .frame import Frame
from .stream import FrameReader, FrameWriter

_LOGGER = logging.getLogger(__name__)

CONNECT_TIMEOUT: Final = 5
RECONNECT_TIMEOUT: Final = 20


class Connection(ABC):
    """Base connection class.

    Attributes:
        kwargs -- keyword arguments for connection driver
        closing -- is connection closing
        writer -- instance of frame writer
        _net -- network information for device available message
        _devices -- collection of all available devices
        _callback_task -- callback task reference
        _callback_closed -- callback to call when connection is closed
    """

    def __init__(self, **kwargs):
        """Creates connection instance.

        Keyword arguments:
            **kwargs -- keyword arguments for connection driver
        """
        self.kwargs = kwargs
        self.closing = False
        self.writer = None
        self._net = {}
        self._devices = DevicesCollection()
        self._callback_task = None
        self._callback_closed = None

    def __enter__(self):
        """Provides entry point for context manager."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Provides exit point for context manager."""

    async def _callback(
        self,
        callback: Callable[[DevicesCollection, Connection], Awaitable[Any]],
        interval: int,
    ) -> None:
        """Calls provided callback method with specified interval.

        Keyword arguments:
            callback -- callback method
            ecomax -- ecoMAX device instance
            interval -- update interval in seconds
        """
        while True:
            try:
                await callback(self._devices, self)
            except Exception:  # pylint: disable=broad-except
                pass

            await asyncio.sleep(interval)

    async def _process(self, frame: Optional[Frame], writer: FrameWriter) -> None:
        """Processes received frame.

        Keyword arguments:
            frame -- instance of received frame
            writer -- instance of writer
        """

        if frame is None or not self._devices.has(frame.sender):
            return None

        device = self._devices.get(frame.sender)
        if isinstance(frame, requests.ProgramVersion):
            writer.queue(frame.response())

        elif isinstance(frame, responses.UID):
            device.uid = frame.data["UID"]
            device.product = frame.data["reg_name"]
            writer.queue(requests.Password(recipient=frame.sender))

        elif isinstance(frame, responses.Password):
            device.password = frame.data

        elif isinstance(frame, (responses.RegData, responses.CurrentData)):
            frame.schema = device.schema
            device.set_data(frame.data)
            if DATA_MIXERS in frame.data:
                device.mixers.set_data(frame.data[DATA_MIXERS])

        elif isinstance(frame, responses.Parameters):
            device.set_parameters(frame.data)

        elif isinstance(frame, responses.MixerParameters):
            device.mixers.set_parameters(frame.data[DATA_MIXERS])

        elif isinstance(frame, responses.DataStructure):
            device.schema = frame.data

        elif isinstance(frame, requests.CheckDevice):
            writer.queue(frame.response(data=self._net))

        writer.collect(device.changes)

    async def _read(self, reader: FrameReader) -> bool:
        """Handles connection reads.

        Keyword arguments:
            reader -- instance of frame reader
        """
        while True:
            if self.closing:
                await self.writer.close()
                await self._close()
                return False

            try:
                frame = await reader.read()
            except FrameTypeError as e:
                _LOGGER.debug("Type error: %s", e)
            except FrameError as e:
                _LOGGER.warning("Frame error: %s", e)
            else:
                asyncio.create_task(self._process(frame, self.writer))
                await self.writer.process_queue()

        return True

    async def task(
        self,
        callback: Callable[[DevicesCollection, Connection], Awaitable[Any]],
        interval: int = 1,
        reconnect_on_failure: bool = True,
    ) -> None:
        """Establishes connection and continuously reads new frames.

        Keyword arguments:
            callback -- user-defined callback method
            interval -- user-defined update interval in seconds
            reconnect_on_failure -- should we try reconnecting on failure
        """
        while True:
            try:
                reader, self.writer = await self.connect()
                await self.writer.write(requests.StartMaster(recipient=ECOMAX_ADDRESS))
                self._callback_task = asyncio.create_task(
                    self._callback(callback, interval)
                )
                if not await self._read(reader):
                    break
            except (
                asyncio.TimeoutError,
                ConnectionRefusedError,
                ConnectionResetError,
                OSError,
                SerialException,
            ) as e:
                if not reconnect_on_failure:
                    raise e

                _LOGGER.error(
                    "Connection to device failed, retrying in %i seconds...",
                    RECONNECT_TIMEOUT,
                )
                await self._close()
                await asyncio.sleep(RECONNECT_TIMEOUT)

    async def _close(self) -> None:
        """Declares connection as closed."""
        await self.async_close()
        self.writer = None
        self.closing = False
        if self._callback_closed is not None:
            await self._callback_closed(self)

    def run(
        self,
        callback: Callable[[DevicesCollection, Connection], Awaitable[Any]],
        interval: int = 1,
        reconnect_on_failure: bool = True,
    ) -> None:
        """Run connection in the event loop.

        Keyword arguments:
            callback -- user-defined callback method
            interval -- user-defined update interval in seconds
            reconnect_on_failure -- should we try reconnecting on failure
        """
        if sys.platform == "win32" and hasattr(
            asyncio, "WindowsSelectorEventLoopPolicy"
        ):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        try:
            sys.exit(asyncio.run(self.task(callback, interval, reconnect_on_failure)))
        except KeyboardInterrupt:
            pass

    def set_eth(
        self, ip: str, netmask: str = DEFAULT_NETMASK, gateway: str = DEFAULT_IP
    ) -> None:
        """Sets eth parameters to pass to devices.
        Used for informational purposes only.

        Keyword arguments:
            ip -- ip address of eth device
            netmask -- netmask of eth device
            gateway -- gateway address of eth device
        """
        eth: Dict[str, Any] = {}
        eth["ip"] = ip
        eth["netmask"] = netmask
        eth["gateway"] = gateway
        eth["status"] = True
        self._net["eth"] = eth

    def set_wlan(
        self,
        ssid: str,
        ip: str,
        encryption: int = WLAN_ENCRYPTION[1],
        netmask: str = DEFAULT_NETMASK,
        gateway: str = DEFAULT_IP,
        quality: int = 100,
    ) -> None:
        """Sets wlan parameters to pass to devices.
        Used for informational purposes only.

        Keyword arguments:
            ssid -- SSID string
            encryption -- wlan encryption, must be passed with constant
            ip -- ip address of wlan device
            netmask -- netmask of wlan device
            gateway -- gateway address of wlan device
        """
        wlan: Dict[str, Any] = {}
        wlan["ssid"] = ssid
        wlan["encryption"] = encryption
        wlan["quality"] = quality
        wlan["ip"] = ip
        wlan["netmask"] = netmask
        wlan["gateway"] = gateway
        wlan["status"] = True
        self._net["wlan"] = wlan

    def on_closed(self, callback: Callable[[Connection], Awaitable[Any]]):
        """Sets callback to be called when connection is closed."""
        self._callback_closed = callback

    def close(self) -> None:
        """Closes connection."""
        if not self.closing:
            self.closing = True
            if self._callback_task is not None:
                self._callback_task.cancel()

    async def async_close(self) -> None:
        """Closes connection asynchronously."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.close)

    @property
    def closed(self) -> bool:
        """Returns connection state."""
        return self.writer is None

    @abstractmethod
    async def connect(self) -> Tuple[FrameReader, FrameWriter]:
        """Initializes connection and returns frame reader and writer."""


class TcpConnection(Connection):
    """Represents TCP connection through.

    Attributes:
        host -- server ip or hostname
        port -- server port
    """

    def __init__(self, host: str, port: int, **kwargs):
        """Creates TCP connection instance."""
        super().__init__(**kwargs)
        self.host = host
        self.port = port

    def __repr__(self):
        """Creates string representation of class."""
        return f"""{self.__class__.__name__}(
    host = {self.host},
    port = {self.port},
    kwargs = {self.kwargs}
)
"""

    async def connect(self) -> Tuple[FrameReader, FrameWriter]:
        """Initializes connection and returns frame reader and writer."""
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host=self.host, port=self.port, **self.kwargs),
            timeout=CONNECT_TIMEOUT,
        )
        return FrameReader(reader), FrameWriter(writer)


class SerialConnection(Connection):
    """Represents serial connection.

    Attributes:
        device -- serial port interface path
        baudrate -- serial port baudrate
    """

    def __init__(self, device: str, baudrate: int = 115200, **kwargs):
        """Creates serial connection instance."""
        super().__init__(**kwargs)
        self.device = device
        self.baudrate = baudrate

    def __repr__(self):
        """Creates string representation of class."""
        return f"""{self.__class__.__name__}(
    device = {self.device},
    baudrate = {self.baudrate},
    kwargs = {self.kwargs}
)
"""

    async def connect(self) -> Tuple[FrameReader, FrameWriter]:
        """Initializes connection and returns frame reader and writer."""
        reader, writer = await asyncio.wait_for(
            serial_asyncio.open_serial_connection(
                url=self.device,
                baudrate=self.baudrate,
                bytesize=serial_asyncio.serial.EIGHTBITS,
                parity=serial_asyncio.serial.PARITY_NONE,
                stopbits=serial_asyncio.serial.STOPBITS_ONE,
                **self.kwargs,
            ),
            timeout=CONNECT_TIMEOUT,
        )
        return FrameReader(reader), FrameWriter(writer)
