"""Contains main ecoNET class, that is used to interact with ecoNET
connection.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import os
import sys

from .devices import EcoMAX
from .exceptions import ChecksumError, LengthError
from .frame import Frame
from .frames import requests, responses
from .storage import FrameBucket
from .stream import FrameReader, FrameWriter


class EcoNET:
    """Allows to interact with ecoNET connection, handles sending and
    receiving frames and calling async callback.
    """

    host: str = None
    port: int = None
    closed: bool = True
    reader: FrameReader = None
    writer: FrameWriter = None

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

    def __enter__(self):
        """Provides entry point for context manager."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Provides exit point for context manager."""
        self.close()

    def __repr__(self):
        """Creates string respresentation of class."""
        return f"""{self.__class__.__name__}(
    host = {self.host},
    port = {self.port},
    kwargs = {self.kwargs}
)
""".strip()

    async def _callback(self, callback: Callable[EcoMAX, EcoNET],
            ecomax: EcoMAX, interval: int) -> None:
        """ Calls provided callback method with specified interval.

        Keyword arguments:
        callback -- callback method
        ecomax -- ecoMAX device instance
        interval -- update interval in seconds
        """
        while True:
            await callback(ecomax = ecomax, econet = self)
            await asyncio.sleep(interval)

    async def _process(self, frame: Frame, ecomax: EcoMAX,
            bucket: FrameBucket) -> None:
        """ Processes received frame.

        Keyword arguments:
        frame -- received Frame instance
        ecomax -- ecoMAX device instance
        bucket -- version storage instance
        """
        if frame.is_type(requests.ProgramVersion):
            self.writer.queue(frame.response())

        elif frame.is_type(responses.UID):
            ecomax.uid = frame.data()['UID']
            ecomax.product = frame.data()['reg_name']

        elif frame.is_type(responses.Password):
            ecomax.password = frame.data()

        elif frame.is_type(responses.CurrentData):
            bucket.fill(frame.data()['frame_versions'])
            ecomax.set_data(frame.data())

        elif frame.is_type(responses.RegData):
            bucket.fill(frame.data()['frame_versions'])

        elif frame.is_type(responses.Parameters):
            ecomax.set_parameters(frame.data())

        elif frame.is_type(responses.DataStructure):
            ecomax.struct = frame.data()

        elif frame.is_type(requests.CheckDevice):
            if self.writer.queue_is_empty():
                # Respond to check device frame only if queue is empty.
                return self.writer.queue(frame.response())

    async def run(self, callback: Callable[EcoMAX, EcoNET],
            interval: int = 1) -> None:
        """Establishes connection and continuously reads new frames.

        Keyword arguments:
        callback -- user-defined callback method
        interval -- user-defined update interval in seconds
        """
        try:
            reader, writer = await asyncio.open_connection(
                host = self.host, port = self.port, **self.kwargs)
        except RuntimeError:
            pass

        self.closed = False
        self.reader, self.writer = [FrameReader(reader), FrameWriter(writer)]
        self.writer.queue(requests.Password())
        bucket = FrameBucket(self.writer)
        ecomax = EcoMAX()
        asyncio.create_task(self._callback(callback, ecomax, interval))
        while True:
            if self.closed:
                self.writer.close()
                return

            try:
                frame = await self.reader.read()
            except ChecksumError:
                pass
            except LengthError:
                pass

            if frame is not None:
                asyncio.create_task(self._process(
                    frame = frame,
                    ecomax = ecomax,
                    bucket = bucket
                ))

            await self.writer.process_queue()

    def loop(self, callback: Callable[EcoMAX, EcoNET],
            interval: int = 1) -> None:
        """Run connection in the event loop.

        Keyword arguments:
        callback -- user-defined callback method
        interval -- user-defined update interval in seconds
        """
        try:
            if os.name == 'nt':
                asyncio.set_event_loop_policy(
                    asyncio.WindowsSelectorEventLoopPolicy())

            sys.exit(asyncio.run(self.run(callback, interval)))
        except KeyboardInterrupt:
            pass

    def close(self) -> None:
        """Closes opened connection."""
        self.closed = True
