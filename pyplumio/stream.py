"""Contains reader and writer classes."""
from __future__ import annotations

import asyncio
from asyncio import StreamReader, StreamWriter
import logging
from typing import Final, Optional, Tuple

from pyplumio import util
from pyplumio.const import ADDR_BROADCAST, ADDR_ECONET
from pyplumio.exceptions import ChecksumError, ReadError
from pyplumio.frames import FRAME_START, HEADER_SIZE, Frame, get_frame_handler
from pyplumio.helpers.factory import factory
from pyplumio.helpers.timeout import timeout

READER_TIMEOUT: Final = 10
WRITER_TIMEOUT: Final = 10

MIN_FRAME_LENGTH: Final = 10
MAX_FRAME_LENGTH: Final = 1000

_LOGGER = logging.getLogger(__name__)


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
        _LOGGER.debug("Sent frame: %s", frame)
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
            header = await self._reader.read(1)
            if header and header[0] == FRAME_START:
                break

        header += await self._reader.read(HEADER_SIZE - 1)
        if len(header) < HEADER_SIZE:
            raise ReadError(f"Header can't be less than {HEADER_SIZE} bytes")

        [
            _,
            length,
            recipient,
            sender,
            sender_type,
            econet_version,
        ] = util.unpack_header(header)

        return header, length, recipient, sender, sender_type, econet_version

    @timeout(READER_TIMEOUT)
    async def read(self) -> Optional[Frame]:
        """Read the frame and return corresponding handler object."""
        (
            header,
            length,
            recipient,
            sender,
            sender_type,
            econet_version,
        ) = await self._read_header()

        if recipient not in (ADDR_ECONET, ADDR_BROADCAST):
            return None

        if length > MAX_FRAME_LENGTH or length < MIN_FRAME_LENGTH:
            raise ReadError(f"Unexpected frame length ({length})")

        try:
            payload = await self._reader.readexactly(length - HEADER_SIZE)
        except asyncio.IncompleteReadError as e:
            raise ReadError(
                "Got an incomplete frame while trying to read "
                + f"'{length - HEADER_SIZE}' bytes"
            ) from e

        if payload[-2] != util.crc(header + payload[:-2]):
            raise ChecksumError(f"Incorrect frame checksum ({payload[-2]})")

        frame = factory(
            get_frame_handler(frame_type=payload[0]),
            recipient=recipient,
            message=payload[1:-2],
            sender=sender,
            sender_type=sender_type,
            econet_version=econet_version,
        )
        _LOGGER.debug("Received frame: %s", frame)

        return frame
