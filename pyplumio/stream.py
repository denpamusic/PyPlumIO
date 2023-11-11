"""Contains a frame reader and writer classes."""
from __future__ import annotations

from asyncio import IncompleteReadError, StreamReader, StreamWriter
import logging
from typing import Final

from pyplumio.const import DeviceType
from pyplumio.exceptions import ChecksumError, ReadError
from pyplumio.frames import FRAME_START, Frame, bcc, get_frame_handler, struct_header
from pyplumio.helpers.factory import factory
from pyplumio.helpers.timeout import timeout

READER_TIMEOUT: Final = 10
WRITER_TIMEOUT: Final = 10

MIN_FRAME_LENGTH: Final = 10
MAX_FRAME_LENGTH: Final = 1000

_LOGGER = logging.getLogger(__name__)


class FrameWriter:
    """Represents a frame writer."""

    _writer: StreamWriter

    def __init__(self, writer: StreamWriter):
        """Initialize a new frame writer."""
        self._writer = writer

    @timeout(WRITER_TIMEOUT)
    async def write(self, frame: Frame) -> None:
        """Write frame to the connection and
        wait for buffer to drain.
        """
        self._writer.write(frame.bytes)
        await self._writer.drain()
        _LOGGER.debug("Sent frame: %s", frame)

    @timeout(WRITER_TIMEOUT)
    async def close(self) -> None:
        """Close the frame writer."""
        self._writer.close()
        await self._writer.wait_closed()


class FrameReader:
    """Represents a frame reader."""

    _reader: StreamReader

    def __init__(self, reader: StreamReader):
        """Initialize a new frame reader."""
        self._reader = reader

    async def _read_header(self) -> tuple[bytes, int, int, int, int, int]:
        """Locate and read a frame header.

        Raises ReadError if header size is too small and OSError on
        broken connection.
        """
        while buffer := await self._reader.read(1):
            if FRAME_START not in buffer:
                continue

            buffer += await self._reader.read(struct_header.size - 1)
            if len(buffer) < struct_header.size:
                raise ReadError(f"Header can't be less than {struct_header.size} bytes")

            [
                _,
                length,
                recipient,
                sender,
                sender_type,
                econet_version,
            ] = struct_header.unpack_from(buffer)

            return (
                buffer,
                length,
                recipient,
                sender,
                sender_type,
                econet_version,
            )

        raise OSError("No data can be read, RS485 connection broken")

    @timeout(READER_TIMEOUT)
    async def read(self) -> Frame | None:
        """Read the frame and return corresponding handler object.

        Raises ReadError on unexpected frame length or incomplete
        frame and raises ChecksumError on incorrect frame checksum.
        """
        (
            header,
            length,
            recipient,
            sender,
            sender_type,
            econet_version,
        ) = await self._read_header()

        if recipient not in (DeviceType.ECONET, DeviceType.ALL):
            return None

        if length > MAX_FRAME_LENGTH or length < MIN_FRAME_LENGTH:
            raise ReadError(f"Unexpected frame length ({length})")

        try:
            payload = await self._reader.readexactly(length - struct_header.size)
        except IncompleteReadError as e:
            raise ReadError(
                "Got an incomplete frame while trying to read "
                + f"'{length - struct_header.size}' bytes"
            ) from e

        if payload[-2] != bcc(header + payload[:-2]):
            raise ChecksumError(f"Incorrect frame checksum ({payload[-2]})")

        frame: Frame = factory(
            get_frame_handler(frame_type=payload[0]),
            recipient=recipient,
            message=payload[1:-2],
            sender=sender,
            sender_type=sender_type,
            econet_version=econet_version,
        )
        _LOGGER.debug("Received frame: %s", frame)

        return frame
