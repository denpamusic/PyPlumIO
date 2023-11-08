"""Contains data type helper classes."""
from __future__ import annotations

from abc import ABC, abstractmethod
import socket
import struct
from typing import Any

from pyplumio.helpers.uid import decode_uid

# Data type structures.
struct_float = struct.Struct("<f")
struct_char = struct.Struct("<b")
struct_short = struct.Struct("<h")
struct_ushort = struct.Struct("<H")
struct_int = struct.Struct("<i")
struct_uint = struct.Struct("<I")
struct_double = struct.Struct("<d")
struct_int64 = struct.Struct("<q")
struct_uint64 = struct.Struct("<Q")


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

    def __eq__(self, other) -> bool:
        """Compare if data type  is equal to other."""
        if isinstance(other, DataType):
            return self._value == other._value

        return self._value == other

    def _slice_data(self, data: bytes) -> bytes:
        """Slice the data to data type size."""
        return data[0 : self.size] if self.size is not None else data

    @classmethod
    def from_bytes(cls, data: bytes, offset: int = 0):
        """Initialize a new data type from bytes."""
        data_type = cls()
        data_type.unpack(data[offset:])
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

    _size: int | None = struct_char.size

    def unpack(self, data: bytes) -> None:
        """Unpack the data."""
        self._value = struct_char.unpack_from(data)[0]


class Short(DataType):
    """Represents a 16 bit integer."""

    _size: int | None = struct_short.size

    def unpack(self, data: bytes) -> None:
        """Unpack the data."""
        self._value = struct_short.unpack_from(data)[0]


class Int(DataType):
    """Represents a 32 bit integer."""

    _size: int | None = struct_int.size

    def unpack(self, data: bytes) -> None:
        """Unpack the data."""
        self._value = struct_int.unpack_from(data)[0]


class Byte(DataType):
    """Represents a byte."""

    _size: int | None = 1

    def unpack(self, data: bytes) -> None:
        """Unpack the data."""
        self._value = ord(self._slice_data(data))


class UnsignedShort(DataType):
    """Represents an unsigned 16 bit integer."""

    _size: int | None = struct_ushort.size

    def unpack(self, data: bytes) -> None:
        """Unpack the data."""
        self._value = struct_ushort.unpack_from(data)[0]


class UnsignedInt(DataType):
    """Represents a unsigned 32 bit integer."""

    _size: int | None = struct_uint.size

    def unpack(self, data: bytes) -> None:
        """Unpack the data."""
        self._value = struct_uint.unpack_from(data)[0]


class Float(DataType):
    """Represents a float."""

    _size: int | None = struct_float.size

    def unpack(self, data: bytes) -> None:
        """Unpack the data."""
        self._value = struct_float.unpack_from(data)[0]


class Undefined8(DataType):
    """Represents an undefined."""

    _size: int | None = 0

    def unpack(self, _: bytes) -> None:
        """Unpack the data."""
        self._value = None


class Double(DataType):
    """Represents a double."""

    _size: int | None = struct_double.size

    def unpack(self, data: bytes) -> None:
        """Unpack the data."""
        self._value = struct_double.unpack_from(data)[0]


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

    _size: int | None = struct_int64.size

    def unpack(self, data: bytes) -> None:
        """Unpack the data."""
        self._value = struct_int64.unpack_from(data)[0]


class UInt64(DataType):
    """Represents a 64 bit unsigned integer."""

    _size: int | None = struct_uint64.size

    def unpack(self, data: bytes) -> None:
        """Unpack the data."""
        self._value = struct_uint64.unpack_from(data)[0]


class IPv4(DataType):
    """Represents an IPv4 address."""

    _size: int | None = 4

    def unpack(self, data: bytes) -> None:
        """Unpack the data."""
        self._value = socket.inet_ntoa(self._slice_data(data))


class IPv6(DataType):
    """Represents an IPv6 address."""

    _size: int | None = 16

    def unpack(self, data: bytes) -> None:
        """Unpack the data."""
        self._value = socket.inet_ntop(socket.AF_INET6, self._slice_data(data))


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


class PascalString(DataType):
    """Represents a Pascal string."""

    def unpack(self, data: bytes) -> None:
        """Unpack the data."""
        self._size = data[0] + 1
        self._value = data[1 : self.size].decode()


class UID(DataType):
    """Represents an UID string."""

    def unpack(self, data: bytes) -> None:
        """Unpack the data."""
        self._size = data[0] + 1
        self._value = decode_uid(data[1 : self.size])


# The regdata type map.
# Links data type classes to their respective data type ids
# in data schema.
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
