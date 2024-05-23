"""Contains frame classes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import cache, reduce
import struct
from typing import TYPE_CHECKING, Any, ClassVar, Final, cast

from pyplumio.const import DeviceType, FrameType
from pyplumio.exceptions import UnknownFrameError
from pyplumio.helpers.factory import create_instance
from pyplumio.utils import ensure_dict, to_camelcase

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


@cache
def is_known_frame_type(frame_type: int) -> bool:
    """Check if frame type is known."""
    try:
        FrameType(frame_type)
        return True
    except ValueError:
        return False


@cache
def get_frame_handler(frame_type: int) -> str:
    """Return handler class path for the frame type."""
    if not is_known_frame_type(frame_type):
        raise UnknownFrameError(f"Unknown frame type ({frame_type})")

    module, type_name = FrameType(frame_type).name.split("_", 1)
    type_name = to_camelcase(
        type_name,
        overrides=frozenset((("uid", "UID"),)),
    )
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
        "recipient_device",
        "sender",
        "sender_device",
        "econet_type",
        "econet_version",
        "_message",
        "_data",
    )

    recipient: DeviceType
    recipient_device: AddressableDevice | None
    sender: DeviceType
    sender_device: AddressableDevice | None
    econet_type: int
    econet_version: int
    frame_type: ClassVar[FrameType]
    _message: bytearray | None
    _data: dict[str, Any] | None

    def __init__(
        self,
        recipient: DeviceType = DeviceType.ALL,
        sender: DeviceType = DeviceType.ECONET,
        econet_type: int = ECONET_TYPE,
        econet_version: int = ECONET_VERSION,
        message: bytearray | None = None,
        data: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Process a frame data and message."""
        self.recipient = recipient
        self.recipient_device = None
        self.sender = sender
        self.sender_device = None
        self.econet_type = econet_type
        self.econet_version = econet_version
        self._data = data if not kwargs else ensure_dict(data, kwargs)
        self._message = message

    def __eq__(self, other: Any) -> bool:
        """Compare if this frame is equal to other."""
        if isinstance(other, Frame):
            return (
                self.recipient,
                self.sender,
                self.econet_type,
                self.econet_version,
                self._message,
                self._data,
            ) == (
                self.recipient,
                self.sender,
                self.econet_type,
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
            f"econet_type={self.econet_type}, "
            f"econet_version={self.econet_version}, "
            f"message={self.message}, "
            f"data={self.data})"
        )

    def __len__(self) -> int:
        """Return a frame length."""
        return self.length

    def hex(self, *args: Any, **kwargs: Any) -> str:
        """Return a frame message represented as hex string."""
        return self.bytes.hex(*args, **kwargs)

    @property
    def data(self) -> dict[str, Any]:
        """Return the frame data."""
        if self._data is None:
            self._data = (
                self.decode_message(self._message) if self._message is not None else {}
            )

        return self._data

    @data.setter
    def data(self, data: dict[str, Any]) -> None:
        """Set the frame data."""
        self._data = data
        self._message = None

    @property
    def message(self) -> bytearray:
        """Return the frame message."""
        if self._message is None:
            self._message = self.create_message(
                self._data if self._data is not None else {}
            )

        return self._message

    @message.setter
    def message(self, message: bytearray) -> None:
        """Set the frame message."""
        self._message = message
        self._data = None

    @property
    def length(self) -> int:
        """Return the frame length in bytes."""
        return (
            struct_header.size
            + FRAME_TYPE_SIZE
            + len(self.message)
            + CRC_SIZE
            + DELIMITER_SIZE
        )

    @property
    def header(self) -> bytearray:
        """Return the frame header."""
        buffer = bytearray(struct_header.size)
        struct_header.pack_into(
            buffer,
            HEADER_OFFSET,
            FRAME_START,
            self.length,
            int(self.recipient),
            int(self.sender),
            self.econet_type,
            self.econet_version,
        )

        return buffer

    @property
    def bytes(self) -> bytes:
        """Return the frame bytes."""
        data = self.header
        data.append(self.frame_type)
        data += self.message
        data.append(bcc(data))
        data.append(FRAME_END)
        return bytes(data)

    @classmethod
    async def create(cls, frame_type: int, **kwargs: Any) -> Frame:
        """Create a frame handler object from frame type."""
        return cast(
            Frame, await create_instance(get_frame_handler(frame_type), **kwargs)
        )

    @abstractmethod
    def create_message(self, data: dict[str, Any]) -> bytearray:
        """Create frame message."""

    @abstractmethod
    def decode_message(self, message: bytearray) -> dict[str, Any]:
        """Decode frame message."""


class Request(Frame):
    """Represents a request."""

    __slots__ = ()

    def create_message(self, data: dict[str, Any]) -> bytearray:
        """Create a frame message."""
        return bytearray()

    def decode_message(self, message: bytearray) -> dict[str, Any]:
        """Decode a frame message."""
        return {}

    def response(self, **kwargs: Any) -> Response | None:
        """Return a response frame."""
        return None


class Response(Frame):
    """Represents a response."""

    __slots__ = ()

    def create_message(self, data: dict[str, Any]) -> bytearray:
        """Create a frame message."""
        return bytearray()

    def decode_message(self, message: bytearray) -> dict[str, Any]:
        """Decode a frame message."""
        return {}


class Message(Response):
    """Represents a message."""

    __slots__ = ()
