"""Contains reader and writer classes."""
from __future__ import annotations

from asyncio import StreamReader, StreamWriter
from typing import Final, Optional

from pyplumio import util
from pyplumio.constants import BROADCAST_ADDRESS, ECONET_ADDRESS
from pyplumio.exceptions import ChecksumError, LengthError, ReadError
from pyplumio.frames import HEADER_SIZE, Frame, get_frame_handler
from pyplumio.helpers.factory import factory
from pyplumio.helpers.timeout import timeout

READER_BUFFER_SIZE: Final = 1000
READER_TIMEOUT: Final = 5
WRITER_TIMEOUT: Final = 5


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

    @timeout(READER_TIMEOUT)
    async def read(self) -> Optional[Frame]:
        """Attempt to read READER_BUFFER_SIZE bytes, find
        valid frame in it and return corresponding frame handler object.
        """
        buffer = await self._reader.read(READER_BUFFER_SIZE)

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

            if recipient in (ECONET_ADDRESS, BROADCAST_ADDRESS):
                # Destination address is econet or broadcast.
                payload = buffer[HEADER_SIZE:length]
                frame_length = HEADER_SIZE + len(payload)
                if frame_length != length:
                    raise LengthError(
                        "incorrect frame length. "
                        + f"Expected {length} bytes, got {frame_length} bytes"
                    )

                if payload[-2] != util.crc(header + payload[:-2]):
                    raise ChecksumError("incorrect frame checksum")

                return factory(
                    get_frame_handler(frame_type=payload[0]),
                    recipient=recipient,
                    message=payload[1:-2],
                    sender=sender,
                    sender_type=sender_type,
                    econet_version=econet_version,
                )

        raise ReadError("unexpected frame length or unknown recipient")
