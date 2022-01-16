"""Contains main ecoNET class, that is used to interact with ecoNET
connection.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import os
import sys

from .constants import DEFAULT_IP, DEFAULT_NETMASK, WLAN_ENCRYPTION
from .devices import EcoMAX
from .exceptions import ChecksumError, FrameTypeError, LengthError
from .frame import Frame
from .frames import requests, responses
from .stream import FrameReader, FrameWriter


class EcoNET:
    """Allows to interact with ecoNET connection, handles sending and
    receiving frames and calling async callback.
    """

    host: str = None
    port: int = None
    closed: bool = True
    _net: dict = {}
    _writer_close = None

    def __init__(self, host: str, port: int, **kwargs):
        """Creates EcoNET connection instance.

        Keyword arguments:
        host -- hostname or ip of rs485 to tcp bridge,
            connected to ecoMAX controller
        port -- port of rs485 to tcp bridge,
            connected to ecoMAX controller
        **kwargs -- keyword arguments directly passed to asyncio's
            create_connection method
        """
        self.host = host
        self.port = port
        self.kwargs = kwargs
        self.ecomax = EcoMAX()

    def __enter__(self):
        """Provides entry point for context manager."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Provides exit point for context manager."""

    def __repr__(self):
        """Creates string respresentation of class."""
        return f"""{self.__class__.__name__}(
    host = {self.host},
    port = {self.port},
    kwargs = {self.kwargs}
)
"""

    async def _callback(
        self, callback: Callable[EcoMAX, EcoNET], interval: int
    ) -> None:
        """Calls provided callback method with specified interval.

        Keyword arguments:
        callback -- callback method
        ecomax -- ecoMAX device instance
        interval -- update interval in seconds
        """
        while True:
            await callback(ecomax=self.ecomax, econet=self)
            await asyncio.sleep(interval)

    async def _process(self, frame: Frame, writer: FrameWriter) -> None:
        """Processes received frame.

        Keyword arguments:
        frame -- instance of received frame
        writer -- instance of writer
        """

        if frame is None:
            return

        if frame.is_type(requests.ProgramVersion):
            writer.queue(frame.response())

        elif frame.is_type(responses.UID):
            self.ecomax.uid = frame.data["UID"]
            self.ecomax.product = frame.data["reg_name"]

        elif frame.is_type(responses.Password):
            self.ecomax.password = frame.data

        elif frame.is_type(responses.RegData) or frame.is_type(responses.CurrentData):
            self.ecomax.set_data(frame.data)

        elif frame.is_type(responses.Parameters):
            self.ecomax.set_parameters(frame.data)

        elif frame.is_type(responses.DataStructure):
            self.ecomax.struct = frame.data

        elif frame.is_type(requests.CheckDevice):
            if writer.queue_is_empty():
                # Respond to check device frame only if queue is empty.
                writer.queue(frame.response(data=self._net))

        writer.collect(self.ecomax.changes)

    async def _read(self, reader: FrameReader, writer: FrameWriter) -> None:
        """Handles connection reads."""
        while True:
            if self.closed:
                await writer.close()
                break

            try:
                frame = await reader.read()
                asyncio.create_task(self._process(frame, writer))
                await writer.process_queue()
            except ChecksumError:
                pass
            except LengthError:
                pass
            except FrameTypeError:
                pass

    async def task(self, callback: Callable[EcoMAX, EcoNET], interval: int = 1) -> None:
        """Establishes connection and continuously reads new frames.

        Keyword arguments:
        callback -- user-defined callback method
        interval -- user-defined update interval in seconds
        """
        reader, writer = await asyncio.open_connection(
            host=self.host, port=self.port, **self.kwargs
        )

        self.closed = False
        reader, writer = [FrameReader(reader), FrameWriter(writer)]
        writer.queue(requests.Password())
        asyncio.create_task(self._callback(callback, interval))
        self._writer_close = writer.close  # Avoid stream garbage collection message.
        await self._read(reader, writer)

    def run(self, callback: Callable[EcoMAX, EcoNET], interval: int = 1) -> None:
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
        """Sets eth parameters to pass to ecoMax device.
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
        """Sets wlan parameters to pass to ecoMAX device.
        Used for informational purpoises only.

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
        return not self.closed

    def close(self) -> None:
        """Closes opened connection."""
        self.closed = True
