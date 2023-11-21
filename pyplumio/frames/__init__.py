"""Contains frame classes."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import cache, reduce
import struct
from typing import TYPE_CHECKING, ClassVar, Final

from pyplumio.const import DeviceType, FrameType
from pyplumio.exceptions import UnknownFrameError
from pyplumio.helpers.typing import EventDataType
from pyplumio.utils import to_camelcase

FRAME_START: Final = 0x68
FRAME_END: Final = 0x16
HEADER_OFFSET: Final = 0
FRAME_TYPE_SIZE: Final = 1
CRC_SIZE: Final = 1
DELIMITER_SIZE: Final = 1
ECONET_TYPE: Final = 48
ECONET_VERSION: Final = 5

# Frame header structure.
struct_header = struct.Struct("<BH4B")

if TYPE_CHECKING:
    from pyplumio.devices import AddressableDevice


def bcc(data: bytes) -> int:
    """Return a block check character."""
    return reduce(lambda x, y: x ^ y, data)


def is_known_frame_type(frame_type: int) -> bool:
    """Check if frame type is known."""
    try:
        FrameType(frame_type)
        return True
    except ValueError:
        return False


def is_known_device_type(device_type: int) -> bool:
    """Check if device type is known."""
    try:
        DeviceType(device_type)
        return True
    except ValueError:
        return False


@cache
def get_frame_handler(frame_type: int) -> str:
    """Return handler class path for the frame type."""
    try:
        frame_type = FrameType(frame_type)
    except ValueError as e:
        raise UnknownFrameError(f"Unknown frame ({frame_type})") from e

    module, type_name = frame_type.name.split("_", 1)
    type_name = to_camelcase(type_name, overrides={"uid": "UID"})
    return f"frames.{module.lower()}s.{type_name}{module.capitalize()}"


@dataclass
class DataFrameDescription:
    """Describes what data is provided by the frame."""

    __slots__ = ("frame_type", "provides")

    frame_type: FrameType
    provides: str


class Frame(ABC):
    """Represents a frame."""

    __slots__ = (
        "recipient",
        "sender",
        "sender_type",
        "econet_version",
        "_message",
        "_data",
    )

    recipient: DeviceType | AddressableDevice | int
    sender: DeviceType | AddressableDevice | int
    sender_type: int
    econet_version: int
    frame_type: ClassVar[FrameType | int]
    _message: bytearray | None
    _data: EventDataType | None

    def __init__(
        self,
        recipient: DeviceType | AddressableDevice | int = DeviceType.ALL,
        sender: DeviceType | AddressableDevice | int = DeviceType.ECONET,
        sender_type: int = ECONET_TYPE,
        econet_version: int = ECONET_VERSION,
        message: bytearray | None = None,
        data: EventDataType | None = None,
    ):
        """Process a frame data and message.

        If message is set, decode it, otherwise create message from the
        provided data.
        """

        args = [recipient, sender]
        for key, arg in enumerate(args):
            if isinstance(arg, int) and is_known_device_type(arg):
                args[key] = DeviceType(arg)

        self.recipient, self.sender = args
        self.sender_type = sender_type
        self.econet_version = econet_version
        self._data = data
        self._message = message

    def __eq__(self, other) -> bool:
        """Compare if this frame is equal to other."""
        if isinstance(other, Frame):
            return (
                self.recipient,
                self.sender,
                self.sender_type,
                self.econet_version,
                self._message,
                self._data,
            ) == (
                self.recipient,
                self.sender,
                self.sender_type,
                self.econet_version,
                self._message,
                self._data,
            )

        raise TypeError

    def __repr__(self) -> str:
        """Return a serializable string representation."""
        return (
            f"{self.__class__.__name__}("
            f"recipient={repr(self.recipient)}, "
            f"sender={repr(self.sender)}, "
            f"sender_type={self.sender_type}, "
            f"econet_version={self.econet_version}, "
            f"message={self.message}, "
            f"data={self.data})"
        )

    def __len__(self) -> int:
        """Return a frame length."""
        return self.length

    def hex(self, *args, **kwargs) -> str:
        """Return a frame message represented as hex string."""
        return self.bytes.hex(*args, **kwargs)

    @property
    def data(self) -> EventDataType:
        """A frame data."""
        if self._data is None:
            self._data = (
                self.decode_message(self._message) if self._message is not None else {}
            )

        return self._data

    @data.setter
    def data(self, data: EventDataType) -> None:
        """A frame data setter."""
        self._data = data
        self._message = None

    @property
    def message(self) -> bytearray:
        """A frame message."""
        if self._message is None:
            self._message = self.create_message(
                self._data if self._data is not None else {}
            )

        return self._message

    @message.setter
    def message(self, message: bytearray) -> None:
        """A frame message setter."""
        self._message = message
        self._data = None

    @property
    def length(self) -> int:
        """Frame length in bytes."""
        return (
            struct_header.size
            + FRAME_TYPE_SIZE
            + len(self.message)
            + CRC_SIZE
            + DELIMITER_SIZE
        )

    @property
    def header(self) -> bytearray:
        """A frame header."""
        buffer = bytearray(struct_header.size)
        struct_header.pack_into(
            buffer,
            HEADER_OFFSET,
            FRAME_START,
            self.length,
            int(self.recipient),
            int(self.sender),
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

    @abstractmethod
    def create_message(self, data: EventDataType) -> bytearray:
        """Create a frame message."""

    @abstractmethod
    def decode_message(self, message: bytearray) -> EventDataType:
        """Decode a frame message."""


class Request(Frame):
    """Represents a request."""

    __slots__ = ()

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

    __slots__ = ()

    def create_message(self, data: EventDataType) -> bytearray:
        """Create a frame message."""
        return bytearray()

    def decode_message(self, message: bytearray) -> EventDataType:
        """Decode a frame message."""
        return {}


class Message(Response):
    """Represents a message."""

    __slots__ = ()
