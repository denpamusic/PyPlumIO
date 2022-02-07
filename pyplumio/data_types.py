"""Contains data type representations for regdata unpacking."""
from __future__ import annotations

from abc import ABC, abstractmethod

from . import util


class Type(ABC):
    """Base representation of data type."""

    def __init__(self, data=None, size: int = None):
        """Creates data type instance."""
        if size is None:
            size = self.size

        if data is not None:
            self._data = data[0:size] if size > 0 else data

    def __repr__(self) -> str:
        """Returns serializable string representation of the class."""
        return f"""{self.__class__.__name__}(
    data = {self._data},
    size = {self.size}
)
""".strip()

    def unpack(self, data):
        """Unpacks data to a given type.

        Keyword arguments:
        data -- data to unpack
        """
        self._data = data[0 : self.size]

    @property
    @abstractmethod
    def value(self):
        """Returns data value."""

    @property
    @abstractmethod
    def size(self) -> int:
        """Returns data size in bytes."""


class Undefined0(Type):
    """Undefined zero-byte representation."""

    @property
    def value(self) -> None:
        """Returns data value."""
        return None

    @property
    def size(self) -> int:
        """Returns data size in bytes."""
        return 0


class SignedChar(Type):
    """Char representation."""

    @property
    def value(self) -> int:
        """Returns data value."""
        return util.unpack_char(self._data)[0]

    @property
    def size(self) -> int:
        """Returns data size in bytes."""
        return 1


class Short(Type):
    """16 bit integer representation."""

    @property
    def value(self) -> int:
        """Returns data value."""
        return util.unpack_short(self._data)[0]

    @property
    def size(self) -> int:
        """Returns data size in bytes."""
        return 2


class Int(Type):
    """32 bit integer representation."""

    @property
    def value(self) -> int:
        """Returns data value."""
        return util.unpack_int(self._data)[0]

    @property
    def size(self) -> int:
        """Returns data size in bytes."""
        return 4


class Byte(Type):
    """Byte representation."""

    @property
    def value(self) -> int:
        """Returns data value."""
        return ord(self._data)

    @property
    def size(self) -> int:
        """Returns data size in bytes."""
        return 1


class UnsignedShort(Type):
    """Unsigned 16 bit integer representation."""

    @property
    def value(self) -> int:
        """Returns data value."""
        return util.unpack_ushort(self._data)

    @property
    def size(self) -> int:
        """Returns data size in bytes."""
        return 2


class UnsignedInt(Type):
    """Unsigned 32 bit integer representation."""

    @property
    def value(self) -> int:
        """Returns data value."""
        return util.unpack_uint(self._data)[0]

    @property
    def size(self) -> int:
        """Returns data size in bytes."""
        return 4


class Float(Type):
    """Float representation."""

    @property
    def value(self) -> float:
        """Returns data value."""
        return util.unpack_float(self._data)[0]

    @property
    def size(self) -> int:
        """Returns data size in bytes."""
        return 4


class Undefined8(Type):
    """Undefined representation."""

    @property
    def value(self) -> None:
        """Returns data value."""
        return None

    @property
    def size(self) -> int:
        """Returns data size in bytes."""
        return 0


class Double(Type):
    """Double representation."""

    @property
    def value(self) -> float:
        """Returns data value."""
        return util.unpack_double(self._data)[0]

    @property
    def size(self) -> int:
        """Returns data size in bytes."""
        return 8


class Boolean(Type):
    """Boolean representation."""

    def __init__(self, data=None, size: int = None):
        """Creates boolean instance.

        Keyword arguments:
        data -- raw data
        """
        self._index = 0
        super().__init__(data, size=1)

    def index(self, index: int) -> int:
        """Returns next bit index in the bit array.

        Keyword arguments:
        index -- current bit array index
        """
        self._index = index
        return 0 if self._index == 7 else self._index + 1

    def unpack(self, data) -> Type:
        """Unpacks data to with given type.

        Keyword arguments:
        data -- data to unpack
        """
        self._data = data[0:1]

    @property
    def value(self) -> bool:
        """Returns data value."""
        return bool(ord(self._data) & (1 << self._index))

    @property
    def size(self) -> int:
        """Returns data size in bytes."""
        return 1 if self._index == 7 else 0


class Int64(Type):
    """64 bit signed integer representation."""

    @property
    def value(self) -> int:
        """Returns data value."""
        return util.unpack_int64(self._data)[0]

    @property
    def size(self) -> int:
        """Returns data size in bytes."""
        return 8


class UInt64(Type):
    """64 bit unsigned integer representation."""

    @property
    def value(self) -> int:
        """Returns data value."""
        return util.unpack_uint64(self._data)[0]

    @property
    def size(self) -> int:
        """Returns data size in bytes."""
        return 8


class IPv4(Type):
    """IPv4 address representation."""

    @property
    def value(self) -> str:
        """Returns data value."""
        return util.ip4_from_bytes(self._data)

    @property
    def size(self) -> int:
        """Returns data size in bytes."""
        return 4


class IPv6(Type):
    """IPv6 address representation."""

    @property
    def value(self) -> str:
        """Returns data value."""
        return util.ip6_from_bytes(self._data)

    @property
    def size(self) -> int:
        """Returns data size in bytes."""
        return 16


class String(Type):
    """Variable length bytes representation."""

    def __init__(self, data=None, size: int = None):
        """Creates variable length type instance."""
        super().__init__(data, size=-1)

    @property
    def value(self) -> str:
        """Returns data value."""
        value = ""
        offset = 0
        while not self._data[offset] == "\x00":
            value += self._data[offset]
            offset += 1

        return value

    @property
    def size(self) -> int:
        """Returns data size in bytes."""
        return len(self.value) + 1