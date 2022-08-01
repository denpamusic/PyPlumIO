"""Contains frame class."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import IntEnum
from typing import ClassVar, Dict, Final, List, Optional

from pyplumio import util
from pyplumio.const import BROADCAST_ADDRESS, ECONET_ADDRESS
from pyplumio.exceptions import UnknownFrameError
from pyplumio.helpers.typing import DeviceDataType, MessageType

FRAME_START: Final = 0x68
FRAME_END: Final = 0x16
HEADER_SIZE: Final = 7
FRAME_TYPE_SIZE: Final = 1
CRC_SIZE: Final = 1
DELIMITER_SIZE: Final = 1
ECONET_TYPE: Final = 0x30
ECONET_VERSION: Final = 0x05


class RequestTypes(IntEnum):
    """Contains request frame types."""

    STOP_MASTER = 0x18
    START_MASTER = 0x19
    CHECK_DEVICE = 0x30
    BOILER_PARAMETERS = 0x31
    MIXER_PARAMETERS = 0x32
    SET_BOILER_PARAMETER = 0x33
    SET_MIXER_PARAMETER = 0x34
    UID = 0x39
    PASSWORD = 0x3A
    BOILER_CONTROL = 0x3B
    PROGRAM_VERSION = 0x40
    DATA_SCHEMA = 0x55
    ALERTS = 0x3D


REQUEST_TYPES = {
    x.value: f"requests.{util.to_camelcase(x.name)}Request" for x in RequestTypes
}


class ResponseTypes(IntEnum):
    """Contains response frame types."""

    DEVICE_AVAILABLE = 0xB0
    UID = 0xB9
    BOILER_PARAMETERS = 0xB1
    MIXER_PARAMETERS = 0xB2
    SET_BOILER_PARAMETER = 0xB3
    SET_MIXER_PARAMETER = 0xB4
    PASSWORD = 0xBA
    BOILER_CONTROL = 0xBB
    PROGRAM_VERSION = 0xC0
    DATA_SCHEMA = 0xD5
    ALERTS = 0xBD


RESPONSE_TYPES = {
    x.value: f"responses.{util.to_camelcase(x.name)}Response" for x in ResponseTypes
}


class MessageTypes(IntEnum):
    """Contains message frame types."""

    REGULATOR_DATA = 0x08
    SENSOR_DATA = 0x35


MESSAGE_TYPES = {
    x.value: f"messages.{util.to_camelcase(x.name)}Message" for x in MessageTypes
}


# Dictionary of frame handler classes indexed by frame types.
FRAME_TYPES: Dict[int, str] = {**REQUEST_TYPES, **RESPONSE_TYPES, **MESSAGE_TYPES}


def get_frame_handler(frame_type: int) -> str:
    """Return class path for the frame type."""
    if frame_type in FRAME_TYPES:
        return f"frames.{FRAME_TYPES[frame_type]}"

    raise UnknownFrameError(f"Unknown frame type ({frame_type})")


@dataclass
class FrameDataClass:
    """Data class mixin for the frame."""

    recipient: int = BROADCAST_ADDRESS
    sender: int = ECONET_ADDRESS
    sender_type: int = ECONET_TYPE
    econet_version: int = ECONET_VERSION
    message: MessageType = field(default_factory=bytearray)
    data: DeviceDataType = field(default_factory=dict)


class Frame(ABC, FrameDataClass):
    """Represents base frame class."""

    frame_type: ClassVar[int]

    def __init__(self, *args, **kwargs):
        """Process frame message and data."""
        super().__init__(*args, **kwargs)

        if not self.message:
            # If message not set, create message bytes from data.
            self.message = self.create_message(self.data)

        if self.message and not self.data:
            # If message is set and data is not, decode message.
            self.data = self.decode_message(self.message)

    def __len__(self) -> int:
        """Return frame length."""
        return self.length

    @abstractmethod
    def create_message(self, data: DeviceDataType) -> MessageType:
        """Create frame message."""

    @abstractmethod
    def decode_message(self, message: MessageType) -> DeviceDataType:
        """Decode frame message."""

    @property
    def length(self) -> int:
        """Return frame length."""
        return (
            HEADER_SIZE
            + FRAME_TYPE_SIZE
            + len(self.message)
            + CRC_SIZE
            + DELIMITER_SIZE
        )

    @property
    def header(self) -> bytearray:
        """Return frame header."""
        buffer = bytearray(HEADER_SIZE)
        util.pack_header(
            buffer,
            0,
            FRAME_START,
            len(self),
            self.recipient,
            self.sender,
            self.sender_type,
            self.econet_version,
        )

        return buffer

    @property
    def bytes(self) -> bytes:
        """Return bytes frame representation."""
        data = self.header
        data.append(self.frame_type)
        data += self.message
        data.append(util.crc(data))
        data.append(FRAME_END)
        return bytes(data)

    @property
    def hex(self) -> List[str]:
        """Return hex frame representation."""
        return util.to_hex(self.bytes)


class Request(Frame):
    """Represents request frame."""

    def create_message(self, data: DeviceDataType) -> MessageType:
        """Create frame message."""
        return bytearray()

    def decode_message(self, message: MessageType) -> DeviceDataType:
        """Decode frame message."""
        return {}

    def response(self, **args) -> Optional[Response]:
        """Return response object for current request."""
        return None


class Response(Frame):
    """Represents response frame."""

    def create_message(self, data: DeviceDataType) -> MessageType:
        """Create frame message."""
        return bytearray()

    def decode_message(self, message: MessageType) -> DeviceDataType:
        """Decode frame message."""
        return {}


class Message(Response):
    """Represents message frame."""
