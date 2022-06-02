"""Contains reader and writer classes."""

from __future__ import annotations

import asyncio
from asyncio import StreamReader, StreamWriter
from typing import Final, List, Optional

from . import util
from .constants import BROADCAST_ADDRESS, ECONET_ADDRESS
from .exceptions import ChecksumError, LengthError
from .factory import FrameFactory
from .frames import HEADER_SIZE, Frame, Request

READER_BUFFER_SIZE: Final = 1000
READER_TIMEOUT: Final = 5
WRITER_TIMEOUT: Final = 5


class FrameWriter:
    """Used to asynchronously write frames to a connection using
    asyncio's StreamWriter and maintains write queue.

    Attributes:
        writer -- instance of asyncio.StreamWriter
        _queue -- request queue
    """

    def __init__(self, writer: StreamWriter):
        """Creates instance of FrameWriter.

        Keyword arguments:
            writer -- instance of asyncio.StreamWriter
        """
        self.writer = writer
        self._queue: List[Request] = []

    def __len__(self) -> int:
        """Gets write queue length."""
        return len(self._queue)

    def queue(self, *frames: Request) -> None:
        """Adds frame to write queue.

        Keyword arguments:
            frame -- Frame instance to add
        """
        for frame in frames:
            if isinstance(frame, Frame) and not self.has(frame):
                self._queue.append(frame)

    def has(self, request: Request) -> bool:
        """Checks if write queue contains specific request.

        Keyword arguments:
            request - request to look for
        """
        for frame in self._queue:
            if frame.frame_type == request.frame_type:
                return True

        return False

    def collect(self, requests: List[Request]) -> None:
        """Collects changed parameters and adds them to write queue.

        Keyword arguments:
            requests -- list of changed parameters
        """
        self.queue(*requests)

    async def process_queue(self) -> None:
        """Processes top-most write request from the stack."""
        if self._queue:
            frame = self._queue.pop(0)
            await self.write(frame)

    async def write(self, frame: Frame) -> None:
        """Writes frame to connection and waits for buffer to drain.

        Keyword arguments:
            frame -- Frame instance to add
        """
        self.writer.write(frame.bytes)
        await asyncio.wait_for(self.writer.drain(), timeout=WRITER_TIMEOUT)

    async def close(self) -> None:
        """Closes stream writer."""
        self.writer.close()
        await asyncio.wait_for(self.writer.wait_closed(), timeout=WRITER_TIMEOUT)

    @property
    def is_empty(self) -> bool:
        """Checks if write queue is empty."""
        return not self._queue


class FrameReader:
    """Used to read and parse received frames
    using asyncio's StreamReader.

    Attributes:
        reader -- instance of asyncio.StreamReader
    """

    def __init__(self, reader: StreamReader):
        """Creates FrameReader instance.

        Keyword arguments:
            reader -- instance of asyncio.StreamReader
        """
        self.reader = reader

    async def read(self) -> Optional[Frame]:
        """Attempts to read READER_BUFFER_SIZE bytes, find
        valid frame in it and return corresponding Frame instance.
        """
        buffer = await asyncio.wait_for(
            self.reader.read(READER_BUFFER_SIZE), timeout=READER_TIMEOUT
        )

        if len(buffer) >= HEADER_SIZE:
            header = buffer[0:HEADER_SIZE]
            [
                _,
                length,
                recipient,
                sender,
                sender_type,
                econet_version,
            ] = util.unpack_header(header)

            if recipient in [ECONET_ADDRESS, BROADCAST_ADDRESS]:
                # Destination address is econet or broadcast.
                payload = buffer[HEADER_SIZE:length]
                frame_length = HEADER_SIZE + len(payload)
                if frame_length != length:
                    raise LengthError(
                        "Incorrect frame length. "
                        + f"Expected {length} bytes, got {frame_length} bytes"
                    )

                if payload[-2] != util.crc(header + payload[:-2]):
                    raise ChecksumError("Incorrect frame checksum.")

                return FrameFactory().get_frame(
                    frame_type=payload[0],
                    recipient=recipient,
                    message=payload[1:-2],
                    sender=sender,
                    sender_type=sender_type,
                    econet_version=econet_version,
                )

        return None
