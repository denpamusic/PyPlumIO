from __future__ import annotations

import asyncio
from collections.abc import Callable
import os
import sys

from .constants import VERSION
from .devices import EcoMax
from .exceptions import ChecksumError, LengthError
from .frame import Frame
from .frames import requests, responses
from .storage import FrameBucket
from .stream import FrameReader, FrameWriter


class EcoNet:


    closed: bool = True

    def __init__(self, host: str, port: str, **kwargs):
        self.host = host
        self.port = port
        self.kwargs = kwargs

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    async def _callback(self, callback: Callable[EcoMax, EcoNet],
            ecomax: EcoMax, interval: int) -> None:
        while True:
            await callback(ecomax = ecomax, connection = self)
            await asyncio.sleep(interval)

    async def _process(self, frame: Frame, writer: FrameWriter,
            ecomax: EcoMax, bucket: FrameBucket) -> None:
        if frame.is_type(requests.ProgramVersion):
            writer.queue(frame.response(data={'version' : VERSION}))

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
            if writer.queue_empty(): return writer.queue(frame.response())

    async def run(self, callback: Callable[EcoMax, EcoNet],
            interval: int = 1) -> None:
        try:
            reader, writer = await asyncio.open_connection(
                host = self.host, port = self.port, **self.kwargs)
        except RuntimeError:
            pass

        self.closed = False
        reader, writer = [FrameReader(reader), FrameWriter(writer)]
        writer.queue(requests.UID())
        writer.queue(requests.Password())
        bucket = FrameBucket(writer)
        ecomax = EcoMax()
        asyncio.create_task(self._callback(callback, ecomax, interval))
        while True:
            if self.closed:
                writer.close()
                return

            try:
                frame = await reader.read()
            except ChecksumError:
                pass
            except LengthError:
                pass

            if frame is not None:
                asyncio.create_task(self._process(
                    frame = frame,
                    writer = writer,
                    ecomax = ecomax,
                    bucket = bucket
                ))

            await writer.process_queue()

    def loop(self, callback: Callable[EcoMax, EcoNet],
            interval: int = 1) -> None:
        try:
            if os.name == 'nt':
                asyncio.set_event_loop_policy(
                    asyncio.WindowsSelectorEventLoopPolicy())

            sys.exit(asyncio.run(self.run(callback, interval)))
        except KeyboardInterrupt:
            pass

    def close(self) -> None:
        self.closed = True
