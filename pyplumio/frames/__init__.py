"""Contains frame classes."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import reduce
import struct
from typing import ClassVar, Final

from pyplumio import util
from pyplumio.const import DeviceType, FrameType
from pyplumio.exceptions import UnknownFrameError
from pyplumio.helpers.typing import EventDataType

FRAME_START: Final = 0x68
FRAME_END: Final = 0x16
HEADER_OFFSET: Final = 0
HEADER_SIZE: Final = 7
FRAME_TYPE_SIZE: Final = 1
CRC_SIZE: Final = 1
DELIMITER_SIZE: Final = 1
ECONET_TYPE: Final = 48
ECONET_VERSION: Final = 5

# Frame header packer and unpacker.
pack_header = struct.Struct("<BH4B").pack_into
unpack_header = struct.Struct("<BH4B").unpack_from


def _handler_class_path(frame_type_name: str) -> str:
    """Return handler class path from module name and frame type
    name.
    """
    module, type_name = frame_type_name.split("_", 1)
    type_name = util.to_camelcase(type_name, overrides={"uid": "UID"})
    return f"{module.lower()}s.{type_name}{module.capitalize()}"


# Dictionary of frame handler classes indexed by frame types.
#
# Example: "24: requests.StopMasterRequest"
FRAME_TYPES: dict[int, str] = {
    frame_type.value: _handler_class_path(frame_type.name) for frame_type in FrameType
}


def bcc(data: bytes) -> int:
    """Return a block check character."""
    return reduce(lambda x, y: x ^ y, data)


def is_known_frame_type(frame_type: int) -> bool:
    """Check if frame type is known."""
    try:
        FrameType(frame_type)
    except ValueError:
        return False

    return True


def get_frame_handler(frame_type: int) -> str:
    """Return handler class path for the frame type."""
    if frame_type in FRAME_TYPES:
        return f"frames.{FRAME_TYPES[frame_type]}"

    raise UnknownFrameError(f"Unknown frame type ({frame_type})")


@dataclass
class DataFrameDescription:
    """Describes what data is provided by the frame."""

    frame_type: FrameType
    provides: str


@dataclass
class FrameDataClass:
    """Represents a frame data class mixin."""

    recipient: int = DeviceType.ALL
    sender: int = DeviceType.ECONET
    sender_type: int = ECONET_TYPE
    econet_version: int = ECONET_VERSION
    message: bytearray = field(default_factory=bytearray)
    data: EventDataType = field(default_factory=dict)


class Frame(ABC, FrameDataClass):
    """Represents a frame."""

    frame_type: ClassVar[int]

    def __init__(self, *args, **kwargs):
        """Process a frame data and message.

        If message is set, decode it, otherwise create message from the
        provided data.
        """
        super().__init__(*args, **kwargs)

        try:
            self.sender = DeviceType(self.sender)
            self.recipient = DeviceType(self.recipient)
        except ValueError:
            pass

        if not self.message:
            # Message not set, create message bytes from data.
            self.message = self.create_message(self.data)

        if self.message and not self.data:
            # Message is set, but data is not, decode message.
            self.data = self.decode_message(self.message)

    def __len__(self) -> int:
        """Return a frame length."""
        return self.length

    def hex(self, *args, **kwargs) -> str:
        """Return a frame message represented as hex string."""
        return self.bytes.hex(*args, **kwargs)

    @abstractmethod
    def create_message(self, data: EventDataType) -> bytearray:
        """Create a frame message."""

    @abstractmethod
    def decode_message(self, message: bytearray) -> EventDataType:
        """Decode a frame message."""

    @property
    def length(self) -> int:
        """Frame length in bytes."""
        return (
            HEADER_SIZE
            + FRAME_TYPE_SIZE
            + len(self.message)
            + CRC_SIZE
            + DELIMITER_SIZE
        )

    @property
    def header(self) -> bytearray:
        """A frame header."""
        buffer = bytearray(HEADER_SIZE)
        pack_header(
            buffer,
            HEADER_OFFSET,
            FRAME_START,
            self.length,
            self.recipient,
            self.sender,
            self.sender_type,
            self.econet_version,
        )

        return buffer

    @property
    def bytes(self) -> bytes:
        """Frame bytes."""
        data = self.header
        data.append(self.frame_type)
        data += self.message
        data.append(bcc(data))
        data.append(FRAME_END)
        return bytes(data)


class Request(Frame):
    """Represents a request."""

    def create_message(self, data: EventDataType) -> bytearray:
        """Create a frame message."""
        return bytearray()

    def decode_message(self, message: bytearray) -> EventDataType:
        """Decode a frame message."""
        return {}

    def response(self, **args) -> Response | None:
        """Return a response frame."""
        return None


class Response(Frame):
    """Represents a response."""

    def create_message(self, data: EventDataType) -> bytearray:
        """Create a frame message."""
        return bytearray()

    def decode_message(self, message: bytearray) -> EventDataType:
        """Decode a frame message."""
        return {}


class Message(Response):
    """Represents a message."""
