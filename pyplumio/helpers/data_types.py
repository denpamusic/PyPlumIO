"""Contains data type helper classes."""
from __future__ import annotations

from abc import ABC, abstractmethod
import socket
import struct
from typing import Any

# Data type unpackers.
unpack_float = struct.Struct("<f").unpack
unpack_char = struct.Struct("<b").unpack
unpack_short = struct.Struct("<h").unpack
unpack_ushort = struct.Struct("<H").unpack
unpack_int = struct.Struct("<i").unpack
unpack_uint = struct.Struct("<I").unpack
unpack_double = struct.Struct("<d").unpack
unpack_int64 = struct.Struct("<q").unpack
unpack_uint64 = struct.Struct("<Q").unpack


def unpack_string(data: bytearray, offset: int = 0) -> str:
    """Unpack a string."""
    strlen = data[offset]
    offset += 1
    return data[offset : offset + strlen + 1].decode()


class DataType(ABC):
    """Represents a base data type."""

    _value: Any
    _size: int | None = None

    def __init__(self, value: Any = None):
        """Initialize a new data type."""
        self._value = value

    def __repr__(self) -> str:
        """Return serializable string representation of the class."""
        return f"{self.__class__.__name__}(value={self._value})"

    def _cut_data(self, data: bytes) -> bytes:
        """Cut the data to a size."""
        return data[0 : self.size] if self.size is not None else data

    @classmethod
    def from_bytes(cls, data: bytes):
        """Initialize a new data type from bytes."""
        data_type = cls()
        data_type.unpack(data)
        return data_type

    @property
    def value(self):
        """A data value."""
        return self._value

    @property
    def size(self) -> int | None:
        """A data size."""
        return self._size

    @abstractmethod
    def unpack(self, data: bytes) -> None:
        """Unpack the data."""


class Undefined0(DataType):
    """Represents an undefined zero-byte."""

    _size: int | None = 0

    def unpack(self, _: bytes) -> None:
        """Unpack the data."""
        self._value = None


class SignedChar(DataType):
    """Represents a signed char."""

    _size: int | None = 1

    def unpack(self, data: bytes) -> None:
        """Unpack the data."""
        self._value = unpack_char(self._cut_data(data))[0]


class Short(DataType):
    """Represents a 16 bit integer."""

    _size: int | None = 2

    def unpack(self, data: bytes) -> None:
        """Unpack the data."""
        self._value = unpack_short(self._cut_data(data))[0]


class Int(DataType):
    """Represents a 32 bit integer."""

    _size: int | None = 4

    def unpack(self, data: bytes) -> None:
        """Unpack the data."""
        self._value = unpack_int(self._cut_data(data))[0]


class Byte(DataType):
    """Represents a byte."""

    _size: int | None = 1

    def unpack(self, data: bytes) -> None:
        """Unpack the data."""
        self._value = ord(self._cut_data(data))


class UnsignedShort(DataType):
    """Represents an unsigned 16 bit integer."""

    _size: int | None = 2

    def unpack(self, data: bytes) -> None:
        """Unpack the data."""
        self._value = unpack_ushort(self._cut_data(data))[0]


class UnsignedInt(DataType):
    """Represents a unsigned 32 bit integer."""

    _size: int | None = 4

    def unpack(self, data: bytes) -> None:
        """Unpack the data."""
        self._value = unpack_uint(self._cut_data(data))[0]


class Float(DataType):
    """Represents a float."""

    _size: int | None = 4

    def unpack(self, data: bytes) -> None:
        """Unpack the data."""
        self._value = unpack_float(self._cut_data(data))[0]


class Undefined8(DataType):
    """Represents an undefined."""

    _size: int | None = 0

    def unpack(self, _: bytes) -> None:
        """Unpack the data."""
        self._value = None


class Double(DataType):
    """Represents a double."""

    _size: int | None = 8

    def unpack(self, data: bytes) -> None:
        """Unpack the data."""
        self._value = unpack_double(self._cut_data(data))[0]


class Boolean(DataType):
    """Represents a boolean."""

    _index: int = 0

    def __init__(self, value: Any = None):
        """Initialize a new boolean."""
        self._index = 0
        super().__init__(value)

    def next(self, index: int = 0) -> int:
        """Set current bit and return the next index in the
        bit array.
        """
        self._index = index
        return 0 if self._index == 7 else self._index + 1

    def unpack(self, data: bytes) -> None:
        """Unpack the data."""
        self._value = ord(data[0:1])

    @property
    def value(self) -> bool | None:
        """A data value."""
        return None if self._value is None else bool(self._value & (1 << self._index))

    @property
    def size(self) -> int | None:
        """A data size."""
        return 1 if self._index == 7 else 0


class Int64(DataType):
    """Represents a 64 bit signed integer."""

    _size: int | None = 8

    def unpack(self, data: bytes) -> None:
        """Unpack the data."""
        self._value = unpack_int64(self._cut_data(data))[0]


class UInt64(DataType):
    """Represents a 64 bit unsigned integer."""

    _size: int | None = 8

    def unpack(self, data: bytes) -> None:
        """Unpack the data."""
        self._value = unpack_uint64(self._cut_data(data))[0]


class IPv4(DataType):
    """Represents an IPv4 address."""

    _size: int | None = 4

    def unpack(self, data: bytes) -> None:
        """Unpack the data."""
        self._value = socket.inet_ntoa(self._cut_data(data))


class IPv6(DataType):
    """Represents an IPv6 address."""

    _size: int | None = 16

    def unpack(self, data: bytes) -> None:
        """Unpack the data."""
        self._value = socket.inet_ntop(socket.AF_INET6, self._cut_data(data))


class String(DataType):
    """Represents a string."""

    def unpack(self, data: bytes) -> None:
        """Unpack the data."""
        value = ""
        if (offset := 0) in data:
            while not data[offset] == 0:
                value += chr(data[offset])
                offset += 1

        self._value = value

    @property
    def size(self) -> int | None:
        """A data size."""
        return len(self.value) + 1 if self.value is not None else None


DATA_TYPES: tuple[type[DataType], ...] = (
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
