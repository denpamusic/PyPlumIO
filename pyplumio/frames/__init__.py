"""Contains frame class."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import IntEnum, unique
from typing import ClassVar, Dict, Final, List, Optional

from pyplumio import util
from pyplumio.const import ADDR_BROADCAST, ADDR_ECONET
from pyplumio.exceptions import UnknownFrameError
from pyplumio.helpers.typing import DeviceDataType, MessageType

FRAME_START: Final = 0x68
FRAME_END: Final = 0x16
HEADER_OFFSET: Final = 0
HEADER_SIZE: Final = 7
FRAME_TYPE_SIZE: Final = 1
CRC_SIZE: Final = 1
DELIMITER_SIZE: Final = 1
ECONET_TYPE: Final = 48
ECONET_VERSION: Final = 5


@unique
class FrameTypes(IntEnum):
    """Contains frame types."""

    REQUEST_STOP_MASTER = 24
    REQUEST_START_MASTER = 25
    REQUEST_CHECK_DEVICE = 48
    REQUEST_BOILER_PARAMETERS = 49
    REQUEST_MIXER_PARAMETERS = 50
    REQUEST_SET_BOILER_PARAMETER = 51
    REQUEST_SET_MIXER_PARAMETER = 52
    REQUEST_SCHEDULES = 54
    REQUEST_SET_SCHEDULE = 55
    REQUEST_UID = 57
    REQUEST_PASSWORD = 58
    REQUEST_BOILER_CONTROL = 59
    REQUEST_ALERTS = 61
    REQUEST_PROGRAM_VERSION = 64
    REQUEST_DATA_SCHEMA = 85
    RESPONSE_DEVICE_AVAILABLE = 176
    RESPONSE_BOILER_PARAMETERS = 177
    RESPONSE_MIXER_PARAMETERS = 178
    RESPONSE_SET_BOILER_PARAMETER = 179
    RESPONSE_SET_MIXER_PARAMETER = 180
    RESPONSE_SCHEDULES = 182
    RESPONSE_UID = 185
    RESPONSE_PASSWORD = 186
    RESPONSE_BOILER_CONTROL = 187
    RESPONSE_ALERTS = 189
    RESPONSE_PROGRAM_VERSION = 192
    RESPONSE_DATA_SCHEMA = 213
    MESSAGE_REGULATOR_DATA = 8
    MESSAGE_SENSOR_DATA = 53


def _handler_class_path(frame_type_name: str) -> str:
    """Return handler class path from module and frame type name."""
    module, type_name = frame_type_name.split("_", 1)

    return f"{module.lower()}s.{util.to_camelcase(type_name)}{module.capitalize()}"


# Dictionary of frame handler classes indexed by frame types.
# example: "24: requests.StopMasterRequest"
FRAME_TYPES: Dict[int, str] = {
    frame_type.value: _handler_class_path(frame_type.name) for frame_type in FrameTypes
}


def is_known_frame_type(frame_type: int) -> bool:
    """Check if frame type is known."""
    try:
        FrameTypes(frame_type)
    except ValueError:
        return False

    return True


def get_frame_handler(frame_type: int) -> str:
    """Return handler class path for the frame type."""
    if frame_type in FRAME_TYPES:
        return f"frames.{FRAME_TYPES[frame_type]}"

    raise UnknownFrameError(f"Unknown frame type ({frame_type})")


@dataclass
class FrameDataClass:
    """Data class mixin for the frame."""

    recipient: int = ADDR_BROADCAST
    sender: int = ADDR_ECONET
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
