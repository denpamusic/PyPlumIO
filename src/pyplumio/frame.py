from __future__ import annotations

from . import util
from .constants import (
    BROADCAST_ADDRESS,
    ECONET_ADDRESS,
    ECONET_TYPE,
    ECONET_VERSION,
    FRAME_END,
    FRAME_START,
    HEADER_SIZE,
)


class Frame:
    """ """

    def __init__(self, type_: int = None, recipient: int = BROADCAST_ADDRESS,
            message: bytearray = bytearray(),
            sender: int = ECONET_ADDRESS,
            sender_type: int = ECONET_TYPE,
            econet_version: int = ECONET_VERSION, data = None):
        self._data = data
        self.recipient = recipient
        self.sender = sender
        self.sender_type = sender_type
        self.econet_version = econet_version
        if type_ is not None:
            self.type_ = type_

        if not message:
            try:
                self.message = self.create_message()
            except NotImplementedError:
                self.message = bytearray()
                pass

        else:
            self.message = message

        # header + type + crc + end
        self.length = HEADER_SIZE + 1 + len(self.message) + 2

    def __repr__(self) -> str:
        name = self.__class__.__name__
        module = self.__module__.rsplit('.', maxsplit=1)[-1]

        return f'{module[:-1]}: {name}'

    def __len__(self) -> int:
        return len(self.to_bytes())

    def data(self):
        if self._data is None:
            self.parse_message(self.message)

        return self._data

    def header(self) -> bytearray:
        buffer = bytearray(HEADER_SIZE)
        util.pack_header(buffer, 0, *[
            FRAME_START,
            self.length,
            self.recipient,
            self.sender,
            self.sender_type,
            self.econet_version
        ])

        return buffer

    def is_type(self, *types) -> bool:
        for type_ in types:
            if isinstance(self, type_):
                return True

        return False

    def to_bytes(self) -> bytes:
        data = self.header()
        data.append(self.type_)
        [ data.append(i) for i in self.message ]
        data.append(util.crc(data))
        data.append(FRAME_END)
        return bytes(data)

    def to_hex(self) -> str:
        return util.to_hex(self.to_bytes())

    def create_message(self) -> bytearray:
        raise NotImplementedError()

    def parse_message(self, message: bytearray) -> None:
        raise NotImplementedError()

    def response(self, **args) -> Frame:
        raise NotImplementedError()
