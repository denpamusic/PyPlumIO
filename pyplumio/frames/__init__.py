"""Contains frame class."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Final, List, Optional

from pyplumio import util
from pyplumio.constants import BROADCAST_ADDRESS, ECONET_ADDRESS
from pyplumio.exceptions import UnknownFrameError
from pyplumio.helpers.classname import ClassName

FRAME_START: Final = 0x68
FRAME_END: Final = 0x16
HEADER_SIZE: Final = 7
FRAME_TYPE_SIZE: Final = 1
CRC_SIZE: Final = 1
DELIMITER_SIZE: Final = 1
ECONET_TYPE: Final = 0x30
ECONET_VERSION: Final = 0x05

# Dictionary of frame handler classes indexed by frame types.
frames: Dict[int, str] = {
    0x18: "requests.StopMaster",
    0x19: "requests.StartMaster",
    0x30: "requests.CheckDevice",
    0x31: "requests.BoilerParameters",
    0x32: "requests.MixerParameters",
    0x33: "requests.SetBoilerParameter",
    0x34: "requests.SetMixerParameter",
    0x39: "requests.UID",
    0x3A: "requests.Password",
    0x3B: "requests.BoilerControl",
    0x40: "requests.ProgramVersion",
    0x55: "requests.DataSchema",
    0xB0: "responses.DeviceAvailable",
    0xB9: "responses.UID",
    0xB1: "responses.BoilerParameters",
    0xB2: "responses.MixerParameters",
    0xB3: "responses.SetBoilerParameter",
    0xB4: "responses.SetMixerParameter",
    0xBA: "responses.Password",
    0xBB: "responses.BoilerControl",
    0xC0: "responses.ProgramVersion",
    0xD5: "responses.DataSchema",
    0x08: "messages.RegulatorData",
    0x35: "messages.SensorData",
}


def get_frame_handler(frame_type: int) -> str:
    """Return class path for the frame type."""
    if frame_type in frames:
        return "frames." + frames[frame_type]

    raise UnknownFrameError(f"unknown frame type {frame_type}")


class Frame(ABC, ClassName):
    """Represents base frame class."""

    frame_type: int
    recipient: int
    message: bytearray
    sender: int
    sender_type: int
    econet_version: int
    _data: Optional[Dict[str, Any]]

    def __init__(
        self,
        frame_type: Optional[int] = None,
        recipient: int = BROADCAST_ADDRESS,
        message: bytearray = bytearray(),
        sender: int = ECONET_ADDRESS,
        sender_type: int = ECONET_TYPE,
        econet_version: int = ECONET_VERSION,
        data: Optional[Dict[str, Any]] = None,
    ):
        """Initialize new Frame object."""
        self._data = data
        self.recipient = recipient
        self.sender = sender
        self.sender_type = sender_type
        self.econet_version = econet_version
        if frame_type is not None:
            self.frame_type = frame_type

        self.message = message if message else self.create_message()

    def __repr__(self) -> str:
        """Return serializable string representation of the class."""
        return f"""{self.get_classname()}(
    type = {self.frame_type},
    recipient = {self.recipient},
    message = {self.message},
    sender = {self.sender},
    sender_type = {self.sender_type},
    econet_version = {self.econet_version},
    data = {self._data}
)
""".strip()

    def __len__(self) -> int:
        """Return frame length."""
        return self.length

    def __eq__(self, other) -> bool:
        """Check if two frames are equal."""
        return repr(self) == repr(other)

    def is_type(self, *args) -> bool:
        """Check if frame is instance of type."""
        return isinstance(self, tuple(args))

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
    def data(self):
        """Return frame data."""
        if self._data is None:
            # If frame data not present.
            self.parse_message(self.message)

        return self._data

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

    @abstractmethod
    def create_message(self) -> bytearray:
        """Create message from the frame data."""

    @abstractmethod
    def parse_message(self, message: bytearray) -> None:
        """Parse message to the frame data."""


class Request(Frame):
    """Represents request frames."""

    def response(self, **args) -> Optional[Frame]:
        """Return response object for current request."""
        return None

    def create_message(self) -> bytearray:
        """Create message from the frame data."""
        return bytearray()

    def parse_message(self, message: bytearray) -> None:
        """Parse message to the frame data."""


class Response(Frame):
    """Represents response frames."""

    def create_message(self) -> bytearray:
        """Create message from the frame data."""
        return bytearray()

    def parse_message(self, message: bytearray) -> None:
        """Parse message to the frame data."""


class Message(Response):
    """Represent message frames."""
