"""Contains main ecoNET class, that is used to interact with ecoNET
connection.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from collections.abc import Callable
import logging
import os
import sys

import serial_asyncio

from .constants import (
    DEFAULT_IP,
    DEFAULT_NETMASK,
    READER_TIMEOUT,
    RECONNECT_TIMEOUT,
    WLAN_ENCRYPTION,
)
from .devices import DeviceCollection
from .exceptions import ChecksumError, FrameTypeError, LengthError
from .frame import Frame
from .frames import requests, responses
from .stream import FrameReader, FrameWriter

_LOGGER = logging.getLogger(__name__)


class EcoNET(ABC):
    """Base ecoNET connection class."""

    def __init__(self, **kwargs):
        """Creates EcoNET connection instance.

        Keyword arguments:
        **kwargs -- keyword arguments directly passed to asyncio's
            create_connection method
        """
        self.kwargs = kwargs
        self.closing = False
        self._net = {}
        self._devices = DeviceCollection()
        self._callback_task = None
        self.writer = None

    def __enter__(self):
        """Provides entry point for context manager."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Provides exit point for context manager."""

    async def _callback(
        self, callback: Callable[DeviceCollection, EcoNET], interval: int
    ) -> None:
        """Calls provided callback method with specified interval.

        Keyword arguments:
        callback -- callback method
        ecomax -- ecoMAX device instance
        interval -- update interval in seconds
        """
        while True:
            await callback(self._devices, econet=self)
            await asyncio.sleep(interval)

    async def _process(self, frame: Frame, writer: FrameWriter) -> None:
        """Processes received frame.

        Keyword arguments:
        frame -- instance of received frame
        writer -- instance of writer
        """

        if frame is None or not self._devices.has(frame.sender):
            return None

        device = self._devices.get(frame.sender)
        if frame.is_type(requests.ProgramVersion):
            writer.queue(frame.response())

        elif frame.is_type(responses.UID):
            device.uid = frame.data["UID"]
            device.product = frame.data["reg_name"]

        elif frame.is_type(responses.Password):
            device.password = frame.data

        elif frame.is_type(responses.RegData) or frame.is_type(responses.CurrentData):
            device.set_data(frame.data)

        elif frame.is_type(responses.Parameters):
            device.set_parameters(frame.data)

        elif frame.is_type(responses.DataStructure):
            device.struct = frame.data

        elif frame.is_type(requests.CheckDevice):
            if writer.queue_is_empty():
                # Respond to check device frame only if queue is empty.
                writer.queue(frame.response(data=self._net))

        writer.collect(device.changes)

    async def _read(self, reader: FrameReader) -> None:
        """Handles connection reads."""
        while True:
            if self.closing:
                await self.writer.close()
                self.writer = None
                self.closing = False
                break

            try:
                frame = await asyncio.wait_for(reader.read(), timeout=READER_TIMEOUT)
            except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
                _LOGGER.error(
                    "Connection to device failed, retrying in %i seconds...",
                    RECONNECT_TIMEOUT,
                )
                reader, self.writer = await self.reconnect()
            except ChecksumError:
                _LOGGER.warning("Incorrect frame checksum.")
            except LengthError:
                _LOGGER.warning("Incorrect frame length.")
            except FrameTypeError:
                _LOGGER.info("Unknown frame type %s.", hex(frame.type_))
            else:
                asyncio.create_task(self._process(frame, self.writer))
                await self.writer.process_queue()

    async def reconnect(self) -> (FrameReader, FrameWriter):
        """Initializes reconnect after RECONNECT_TIMEOUT seconds."""
        if self.connected():
            await self.writer.close()

        await asyncio.sleep(RECONNECT_TIMEOUT)
        return await self.connect()

    async def task(
        self, callback: Callable[DeviceCollection, EcoNET], interval: int = 1
    ) -> None:
        """Establishes connection and continuously reads new frames.

        Keyword arguments:
        callback -- user-defined callback method
        interval -- user-defined update interval in seconds
        """
        reader, self.writer = await self.connect()
        self.writer.queue(requests.Password())
        self._callback_task = asyncio.create_task(self._callback(callback, interval))
        await self._read(reader)

    def run(
        self, callback: Callable[DeviceCollection, EcoNET], interval: int = 1
    ) -> None:
        """Run connection in the event loop.

        Keyword arguments:
        callback -- user-defined callback method
        interval -- user-defined update interval in seconds
        """
        if os.name == "nt":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        try:
            sys.exit(asyncio.run(self.task(callback, interval)))
        except KeyboardInterrupt:
            pass

    def set_eth(
        self, ip: str, netmask: str = DEFAULT_NETMASK, gateway: str = DEFAULT_IP
    ) -> None:
        """Sets eth parameters to pass to devices.
        Used for informational purpoises only.

        Keyword arguments:
        ip -- ip address of eth device
        netmask -- netmask of eth device
        gateway -- gateway address of eth device
        """
        eth = {}
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
        wlan = {}
        wlan["ssid"] = ssid
        wlan["encryption"] = encryption
        wlan["quality"] = quality
        wlan["ip"] = ip
        wlan["netmask"] = netmask
        wlan["gateway"] = gateway
        wlan["status"] = True
        self._net["wlan"] = wlan

    def connected(self) -> bool:
        """Returns connection state."""
        return self.writer is not None

    def close(self) -> None:
        """Closes opened connection."""
        if not self.closing:
            self.closing = True
            if self._callback_task is not None:
                self._callback_task.cancel()

    @abstractmethod
    async def connect(self) -> (FrameReader, FrameWriter):
        """Initializes connection and returns frame reader and writer."""


class TcpConnection(EcoNET):
    """Represents ecoNET TCP connection through."""

    def __init__(self, host: str, port: int, **kwargs):
        """Creates EcoNET TCP connection instance."""
        super().__init__(**kwargs)
        self.host = host
        self.port = port

    def __repr__(self):
        """Creates string respresentation of class."""
        return f"""{self.__class__.__name__}(
    host = {self.host},
    port = {self.port},
    kwargs = {self.kwargs}
)
"""

    async def connect(self) -> (FrameReader, FrameWriter):
        """Initializes connection and returns frame reader and writer."""
        reader, writer = await asyncio.open_connection(
            host=self.host, port=self.port, **self.kwargs
        )
        return [FrameReader(reader), FrameWriter(writer)]


class SerialConnection(EcoNET):
    """Represents ecoNET serial connection."""

    def __init__(self, device: str, baudrate: int = 115200, **kwargs):
        """Creates EcoNET serial connection instance."""
        super().__init__(**kwargs)
        self.device = device
        self.baudrate = baudrate

    def __repr__(self):
        """Creates string respresentation of class."""
        return f"""{self.__class__.__name__}(
    device = {self.device},
    baudrate = {self.baudrate},
    kwargs = {self.kwargs}
)
"""

    async def connect(self) -> (FrameReader, FrameWriter):
        """Initializes connection and returns frame reader and writer."""
        reader, writer = await serial_asyncio.open_serial_connection(
            url=self.device,
            baudrate=self.baudrate,
            bytesize=serial_asyncio.serial.EIGHTBITS,
            parity=serial_asyncio.serial.PARITY_NONE,
            stopbits=serial_asyncio.serial.STOPBITS_ONE,
            **self.kwargs,
        )
        return [FrameReader(reader), FrameWriter(writer)]
