from __future__ import annotations

from asyncio import StreamReader, StreamWriter

from pyplumio.constants import BROADCAST_ADDRESS, ECONET_ADDRESS, HEADER_SIZE

from . import util
from .exceptions import ChecksumError, FrameTypeError, LengthError
from .factory import FrameFactory
from .frame import Frame


class FrameWriter:
    """ """

    _queue: list = []

    def __init__(self, writer: StreamWriter):
        self.writer = writer

    def __len__(self) -> int:
        return len(self._queue)

    def queue(self, frame: Frame) -> None:
        if isinstance(frame, Frame):
            self._queue.append(frame)

    def queue_empty(self) -> bool:
        return len(self._queue) == 0

    async def process_queue(self) -> None:
        if len(self._queue) > 0:
            frame = self._queue.pop(0)
            await self.write(frame)

    async def write(self, frame: Frame) -> None:
        self.writer.write(frame.to_bytes())
        await self.writer.drain()

    def close(self) -> None:
        self.writer.close()

class FrameReader:
    """ """

    BUFFER_SIZE: int = 1000

    def __init__(self, reader: StreamReader):
        self.reader = reader

    async def read(self) -> Frame:
        buffer = await self.reader.read(FrameReader.BUFFER_SIZE)

        if len(buffer) >= HEADER_SIZE:
            header = buffer[ 0 : HEADER_SIZE ]
            [
                _,
                length,
                recipient,
                sender,
                sender_type,
                econet_version
            ] = util.unpack_header(header)

            if recipient in [ECONET_ADDRESS, BROADCAST_ADDRESS]:
                """Process frame only if destination is our address
                    or broadcast.
                """
                payload = buffer[HEADER_SIZE : length]

                if HEADER_SIZE + len(payload) != length:
                    raise LengthError()

                if payload[-2] != util.crc(header + payload[:-2]):
                    raise ChecksumError()

                try:
                    return FrameFactory.get_frame(
                        type_ = payload[0],
                        recipient = recipient,
                        message = payload[1:-2],
                        sender = sender,
                        sender_type = sender_type,
                        econet_version = econet_version
                    )
                except FrameTypeError:
                    pass
