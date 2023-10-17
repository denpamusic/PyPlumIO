"""Contains data type helper classes."""
from __future__ import annotations

from abc import ABC, abstractmethod
import socket
from typing import Type

from pyplumio import util


class DataType(ABC):
    """Represents base data type."""

    _data: bytes = bytearray()

    def __init__(self, data: bytes | None = None, size: int | None = None):
        """Initialize a new data type."""
        size = self.size if size is None else size

        if data is not None:
            self._data = data[0:size] if size > 0 else data

    def __eq__(self, other) -> bool:
        """Check if two data types are equal."""
        return self._data == other._data and self.size == other.size

    def __repr__(self) -> str:
        """Return serializable string representation of the class."""
        return f"{self.__class__.__name__}(data={self._data!r}, size={self.size})"

    def unpack(self, data: bytes):
        """Unpack data to a given type."""
        self._data = data[0 : self.size]

    @property
    @abstractmethod
    def value(self):
        """A data value."""

    @property
    @abstractmethod
    def size(self) -> int:
        """A data length."""


class Undefined0(DataType):
    """Represents an undefined zero-byte."""

    @property
    def value(self) -> None:
        """A data value."""
        return None

    @property
    def size(self) -> int:
        """A data length."""
        return 0


class SignedChar(DataType):
    """Represents a signed char."""

    @property
    def value(self) -> int:
        """A data value."""
        return util.unpack_char(self._data)[0]

    @property
    def size(self) -> int:
        """A data length."""
        return 1


class Short(DataType):
    """Represents a 16 bit integer."""

    @property
    def value(self) -> int:
        """A data value."""
        return util.unpack_short(self._data)[0]

    @property
    def size(self) -> int:
        """A data length."""
        return 2


class Int(DataType):
    """Represents a 32 bit integer."""

    @property
    def value(self) -> int:
        """A data value."""
        return util.unpack_int(self._data)[0]

    @property
    def size(self) -> int:
        """A data length."""
        return 4


class Byte(DataType):
    """Represents a byte."""

    @property
    def value(self) -> int:
        """A data value."""
        return ord(self._data)

    @property
    def size(self) -> int:
        """A data length."""
        return 1


class UnsignedShort(DataType):
    """Represents an unsigned 16 bit integer."""

    @property
    def value(self) -> int:
        """A data value."""
        return util.unpack_ushort(self._data)[0]

    @property
    def size(self) -> int:
        """A data length."""
        return 2


class UnsignedInt(DataType):
    """Represents a unsigned 32 bit integer."""

    @property
    def value(self) -> int:
        """A data value."""
        return util.unpack_uint(self._data)[0]

    @property
    def size(self) -> int:
        """A data length."""
        return 4


class Float(DataType):
    """Representats a float."""

    @property
    def value(self) -> float:
        """A data value."""
        return util.unpack_float(self._data)[0]

    @property
    def size(self) -> int:
        """A data length."""
        return 4


class Undefined8(DataType):
    """Represents an undefined."""

    @property
    def value(self) -> None:
        """A data value."""
        return None

    @property
    def size(self) -> int:
        """A data length."""
        return 0


class Double(DataType):
    """Represents a double."""

    @property
    def value(self) -> float:
        """A data value."""
        return util.unpack_double(self._data)[0]

    @property
    def size(self) -> int:
        """A data length."""
        return 8


class Boolean(DataType):
    """Represents a boolean."""

    _index: int = 0

    def __init__(self, data: bytes | None = None, size: int | None = 1):
        """Initialize a new boolean."""
        self._index = 0
        super().__init__(data, size)

    def index(self, index: int) -> int:
        """Return next bit index in the bit array."""
        self._index = index
        return 0 if self._index == 7 else self._index + 1

    def unpack(self, data: bytes) -> None:
        """Unpack data to with given type."""
        self._data = data[0:1]

    @property
    def value(self) -> bool:
        """A data value."""
        return bool(ord(self._data) & (1 << self._index))

    @property
    def size(self) -> int:
        """A data length."""
        return 1 if self._index == 7 else 0


class Int64(DataType):
    """Represents a 64 bit signed integer."""

    @property
    def value(self) -> int:
        """A data value."""
        return util.unpack_int64(self._data)[0]

    @property
    def size(self) -> int:
        """A data length."""
        return 8


class UInt64(DataType):
    """Represents a 64 bit unsigned integer."""

    @property
    def value(self) -> int:
        """A data value."""
        return util.unpack_uint64(self._data)[0]

    @property
    def size(self) -> int:
        """A data length."""
        return 8


class IPv4(DataType):
    """Represents an IPv4 address."""

    @property
    def value(self) -> str:
        """A data value."""
        return socket.inet_ntoa(self._data)

    @property
    def size(self) -> int:
        """A data length."""
        return 4


class IPv6(DataType):
    """Represents an IPv6 address."""

    @property
    def value(self) -> str:
        """A data value."""
        return socket.inet_ntop(socket.AF_INET6, self._data)

    @property
    def size(self) -> int:
        """A data length."""
        return 16


class String(DataType):
    """Represents a string."""

    def __init__(self, data: bytes | None = None, size: int | None = -1):
        """Initialize a new string."""
        super().__init__(data, size)

    def unpack(self, data: bytes):
        """Unpack data to a given type."""
        self._data = data
        super().unpack(self._data)

    @property
    def value(self) -> str:
        """A data value."""
        value = ""
        offset = 0
        if offset in self._data:
            while not self._data[offset] == 0:
                value += chr(self._data[offset])
                offset += 1

        return value

    @property
    def size(self) -> int:
        """A data length."""
        return len(self.value) + 1


DATA_TYPES: tuple[Type[DataType], ...] = (
    Undefined0,
    SignedChar,
    Short,
    Int,
    Byte,
    UnsignedShort,
    UnsignedInt,
    Float,
    Undefined8,
    Double,
    Boolean,
    String,
    String,
    Int64,
    UInt64,
    IPv4,
    IPv6,
)
