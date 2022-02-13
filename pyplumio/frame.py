"""Contains frame class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Final, List, Optional

from . import util

FRAME_START: Final = 0x68
FRAME_END: Final = 0x16
HEADER_SIZE: Final = 7
BROADCAST_ADDRESS: Final = 0x00
ECONET_ADDRESS: Final = 0x56
ECONET_TYPE: Final = 0x30
ECONET_VERSION: Final = 0x05


class Frame(ABC):
    """Used as base class for creating and parsing request and response
    frames.

    Attributes:
        type_ -- frame type
        recipient -- recipient address
        sender -- sender address
        sender_type -- sender type
        econet_version -- econet version
        message -- frame body
        _data -- unpacked frame data
    """

    def __init__(
        self,
        type_: int = None,
        recipient: int = BROADCAST_ADDRESS,
        message: bytearray = bytearray(),
        sender: int = ECONET_ADDRESS,
        sender_type: int = ECONET_TYPE,
        econet_version: int = ECONET_VERSION,
        data=None,
    ):
        """Creates new Frame object.

        Keyword arguments:
            type_ -- integer repsentation of frame type
            recipient -- integer repsentation of recipient address
            message -- frame body as bytearray
            sender -- integer respresentation of sender address
            sender_type -- sender type
            econet_version -- version of econet protocol
            data -- frame data, that is used to construct frame message
        """
        self._data = data
        self.recipient = recipient
        self.sender = sender
        self.sender_type = sender_type
        self.econet_version = econet_version
        if type_ is not None:
            self.type_ = type_

        if not message:
            # If frame message is not passed in constructor.
            try:
                self.message = self.create_message()
            except NotImplementedError:
                self.message = bytearray()

        else:
            self.message = message

    def __repr__(self) -> str:
        """Returns serializable string representation of the class."""
        return f"""{self.__class__.__name__}(
    type = {self.type_},
    recipient = {self.recipient},
    message = {self.message},
    sender = {self.sender},
    sender_type = {self.sender_type},
    econet_version = {self.econet_version},
    data = {self._data}
)
""".strip()

    @property
    def length(self) -> int:
        """Returns frame length.

        Structure:
            HEADER_SIZE bytes
            + 1 bytes frame type
            + length of message
            + 1 byte crc
            + 1 byte end delimiter
        """
        return HEADER_SIZE + 1 + len(self.message) + 1 + 1

    def __len__(self) -> int:
        """Returns frame length when calling len() on class instance."""
        return self.length

    @property
    def data(self):
        """Gets data parsed from frame."""
        if self._data is None:
            # If frame data not present.
            self.parse_message(self.message)

        return self._data

    @property
    def header(self) -> bytearray:
        """Gets frame header as bytearray."""
        buffer = bytearray(HEADER_SIZE)
        util.pack_header(
            buffer,
            0,
            *[
                FRAME_START,
                len(self),
                self.recipient,
                self.sender,
                self.sender_type,
                self.econet_version,
            ],
        )

        return buffer

    @property
    def bytes(self) -> bytes:
        """Converts frame to bytes respresentation."""
        data = self.header
        data.append(self.type_)
        data += self.message
        data.append(util.crc(data))
        data.append(FRAME_END)
        return bytes(data)

    @property
    def hex(self) -> List[str]:
        """Converts frame to list of hex bytes."""
        return util.to_hex(self.bytes)

    @abstractmethod
    def create_message(self) -> bytearray:
        """Creates message from the provided data."""

    @abstractmethod
    def parse_message(self, message: bytearray) -> None:
        """Parses data from the frame message.

        Keyword arguments:
            message - bytearray message to parse
        """


class Request(Frame):
    """Base class for all requests frames."""

    def response(self, **args) -> Optional[Frame]:  # pylint: disable=no-self-use
        """Returns instance of Frame
        for response to request, if needed.

        Keyword arguments:
            args -- arguments to pass to response frame constructor
        """
        return None

    def create_message(self) -> bytearray:
        """Creates message from the provided data."""
        return bytearray()

    def parse_message(self, message: bytearray) -> None:
        """Parses data from the frame message.

        Keyword arguments:
            message - bytearray message to parse
        """


class Response(Frame):
    """Base class for all response frames."""

    def create_message(self) -> bytearray:
        """Creates  message from the provided data."""
        return bytearray()

    def parse_message(self, message: bytearray) -> None:
        """Parses data from the frame message.

        Keyword arguments:
        message - bytearray message to parse
        """
