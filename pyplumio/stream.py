"""Contains reader and writer classes."""

from __future__ import annotations

from asyncio import StreamReader, StreamWriter

from pyplumio.constants import BROADCAST_ADDRESS, ECONET_ADDRESS, HEADER_SIZE

from . import util
from .exceptions import ChecksumError, FrameTypeError, LengthError
from .factory import FrameFactory
from .frame import Frame


class FrameWriter:
    """Used to asynchronously write frames to a connection using
    asyncio's StreamWriter and maintains write queue.
    """

    _queue: list = []

    def __init__(self, writer: StreamWriter):
        """Creates instance of FrameWriter.

        Keyword arguments:
        writer -- instance of asyncio.StreamWriter
        """
        self.writer = writer

    def __len__(self) -> int:
        """Gets write queue length."""
        return len(self._queue)

    def queue(self, frame: Frame) -> None:
        """Adds frame to write queue.

        Keyword arguments:
        frame -- Frame instance to add
        """
        if isinstance(frame, Frame):
            self._queue.append(frame)

    def queue_is_empty(self) -> bool:
        """Checks if write queue is empty."""
        return len(self._queue) == 0

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
        self.writer.write(frame.to_bytes())
        await self.writer.drain()

    def close(self) -> None:
        """Closes StreamWriter."""
        self.writer.close()


class FrameReader:
    """Used to read and parse received frames
    using asyncio's StreamReader.
    """

    BUFFER_SIZE: int = 1000

    def __init__(self, reader: StreamReader):
        """Creates FrameReader instance.

        Keyword arguments:
        reader -- instance of asyncio.StreamReader
        """
        self.reader = reader

    async def read(self) -> Frame:
        """Attempts to read FrameReader.BUFFER_SIZE bytes, find
        valid frame in it and return corresponding Frame instance.
        """
        buffer = await self.reader.read(FrameReader.BUFFER_SIZE)

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

                if HEADER_SIZE + len(payload) != length:
                    raise LengthError()

                if payload[-2] != util.crc(header + payload[:-2]):
                    raise ChecksumError()

                try:
                    return FrameFactory().get_frame(
                        type_=payload[0],
                        recipient=recipient,
                        message=payload[1:-2],
                        sender=sender,
                        sender_type=sender_type,
                        econet_version=econet_version,
                    )
                except FrameTypeError:
                    pass
