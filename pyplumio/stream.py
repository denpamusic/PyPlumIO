"""Contains reader and writer classes."""
from __future__ import annotations

from asyncio import StreamReader, StreamWriter
from typing import Final, Optional, Tuple

from pyplumio import util
from pyplumio.const import BROADCAST_ADDRESS, ECONET_ADDRESS
from pyplumio.exceptions import ChecksumError
from pyplumio.frames import FRAME_START, HEADER_SIZE, Frame, get_frame_handler
from pyplumio.helpers.factory import factory
from pyplumio.helpers.timeout import timeout

READER_TIMEOUT: Final = 10
WRITER_TIMEOUT: Final = 10


class FrameWriter:
    """Represents frame writer."""

    _writer: StreamWriter

    def __init__(self, writer: StreamWriter):
        """Initialize new Frame Writer object."""
        self._writer = writer

    @timeout(WRITER_TIMEOUT)
    async def write(self, frame: Frame) -> None:
        """Write frame to the connection and
        wait for buffer to drain."""
        self._writer.write(frame.bytes)
        await self._writer.drain()

    @timeout(WRITER_TIMEOUT)
    async def close(self) -> None:
        """Close the stream writer."""
        self._writer.close()
        await self._writer.wait_closed()


class FrameReader:
    """Represents frame reader."""

    _reader: StreamReader

    def __init__(self, reader: StreamReader):
        """Initialize new Frame Reader object."""
        self._reader = reader

    async def _read_header(self) -> Tuple[bytes, int, int, int, int, int]:
        """Locate and read frame header."""
        while True:
            buffer = await self._reader.read(1)
            if buffer and buffer[0] == FRAME_START:
                break

        buffer += await self._reader.read(HEADER_SIZE - 1)
        header = buffer[0:HEADER_SIZE]
        [
            _,
            length,
            recipient,
            sender,
            sender_type,
            econet_version,
        ] = util.unpack_header(header)
        buffer += await self._reader.read(length - HEADER_SIZE)

        return buffer, length, recipient, sender, sender_type, econet_version

    @timeout(READER_TIMEOUT)
    async def read(self) -> Optional[Frame]:
        """Read the frame and return corresponding handler object."""
        (
            frame,
            length,
            recipient,
            sender,
            sender_type,
            econet_version,
        ) = await self._read_header()

        if recipient in (ECONET_ADDRESS, BROADCAST_ADDRESS):
            # Destination address is econet or broadcast.
            payload = frame[HEADER_SIZE:length]

            if payload[-2] != util.crc(frame[:-2]):
                raise ChecksumError("incorrect frame checksum")

            return factory(
                get_frame_handler(frame_type=payload[0]),
                recipient=recipient,
                message=payload[1:-2],
                sender=sender,
                sender_type=sender_type,
                econet_version=econet_version,
            )

        return None
