"""Contains data type representations."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Tuple, Type

from pyplumio import util
from pyplumio.helpers.typing import BytesType


class DataType(ABC):
    """Represents base data type."""

    _data: BytesType = bytearray()

    def __init__(self, data: Optional[BytesType] = None, size: Optional[int] = None):
        """Initialize new Data Type object."""
        if size is None:
            size = self.size

        if data is not None:
            self._data = data[0:size] if size > 0 else data

    def __eq__(self, other) -> bool:
        """Check if two data types are equal."""
        return self._data == other._data and self.size == other.size

    def __repr__(self) -> str:
        """Return serializable string representation of the class."""
        return f"{self.__class__.__name__}(data={self._data!r}, size={self.size})"

    def unpack(self, data: BytesType):
        """Unpack data to a given type."""
        self._data = data[0 : self.size]

    @property
    @abstractmethod
    def value(self):
        """Return data value."""

    @property
    @abstractmethod
    def size(self) -> int:
        """Return data length."""


class Undefined0(DataType):
    """Represents undefined zero-byte data type."""

    @property
    def value(self) -> None:
        """Return data value."""
        return None

    @property
    def size(self) -> int:
        """Return data length."""
        return 0


class SignedChar(DataType):
    """Represents signed char data type."""

    @property
    def value(self) -> int:
        """Return data value."""
        return util.unpack_char(self._data)[0]

    @property
    def size(self) -> int:
        """Return data length."""
        return 1


class Short(DataType):
    """Represents 16 bit integer data type."""

    @property
    def value(self) -> int:
        """Return data value."""
        return util.unpack_short(self._data)[0]

    @property
    def size(self) -> int:
        """Return data length."""
        return 2


class Int(DataType):
    """Represents 32 bit integer data type."""

    @property
    def value(self) -> int:
        """Return data value."""
        return util.unpack_int(self._data)[0]

    @property
    def size(self) -> int:
        """Return data length."""
        return 4


class Byte(DataType):
    """Represents byte data type."""

    @property
    def value(self) -> int:
        """Return data value."""
        return ord(self._data)

    @property
    def size(self) -> int:
        """Return data length."""
        return 1


class UnsignedShort(DataType):
    """Represents unsigned 16 bit integer data type."""

    @property
    def value(self) -> int:
        """Return data value."""
        return util.unpack_ushort(self._data)

    @property
    def size(self) -> int:
        """Return data length."""
        return 2


class UnsignedInt(DataType):
    """Represents unsigned 32 bit integer data type."""

    @property
    def value(self) -> int:
        """Return data value."""
        return util.unpack_uint(self._data)[0]

    @property
    def size(self) -> int:
        """Return data length."""
        return 4


class Float(DataType):
    """Representats float data type."""

    @property
    def value(self) -> float:
        """Return data value."""
        return util.unpack_float(self._data)[0]

    @property
    def size(self) -> int:
        """Return data length."""
        return 4


class Undefined8(DataType):
    """Represents undefined data type."""

    @property
    def value(self) -> None:
        """Return data value."""
        return None

    @property
    def size(self) -> int:
        """Return data length."""
        return 0


class Double(DataType):
    """Represents double data type."""

    @property
    def value(self) -> float:
        """Return data value."""
        return util.unpack_double(self._data)[0]

    @property
    def size(self) -> int:
        """Return data length."""
        return 8


class Boolean(DataType):
    """Represents boolean data type."""

    _index: int = 0

    def __init__(self, data: Optional[BytesType] = None, size: Optional[int] = None):
        """Initialize new Boolean object."""
        self._index = 0
        super().__init__(data, size=1)

    def index(self, index: int) -> int:
        """Return next bit index in the bit array."""
        self._index = index
        return 0 if self._index == 7 else self._index + 1

    def unpack(self, data: BytesType) -> None:
        """Unpack data to with given type."""
        self._data = data[0:1]

    @property
    def value(self) -> bool:
        """Return data value."""
        return bool(ord(self._data) & (1 << self._index))

    @property
    def size(self) -> int:
        """Return data length."""
        return 1 if self._index == 7 else 0


class Int64(DataType):
    """Represents 64 bit signed integer data type."""

    @property
    def value(self) -> int:
        """Return data value."""
        return util.unpack_int64(self._data)[0]

    @property
    def size(self) -> int:
        """Return data length."""
        return 8


class UInt64(DataType):
    """Represents 64 bit unsigned integer data type."""

    @property
    def value(self) -> int:
        """Return data value."""
        return util.unpack_uint64(self._data)[0]

    @property
    def size(self) -> int:
        """Return data length."""
        return 8


class IPv4(DataType):
    """Represents IPv4 address data type."""

    @property
    def value(self) -> str:
        """Return data value."""
        return util.ip4_from_bytes(self._data)

    @property
    def size(self) -> int:
        """Return data length."""
        return 4


class IPv6(DataType):
    """Represents IPv6 address data type."""

    @property
    def value(self) -> str:
        """Return data value."""
        return util.ip6_from_bytes(self._data)

    @property
    def size(self) -> int:
        """Return data length."""
        return 16


class String(DataType):
    """Represents string data type."""

    def __init__(self, data: Optional[BytesType] = None, size: Optional[int] = None):
        """Initialize new String object."""
        super().__init__(data, size=-1)

    def unpack(self, data: BytesType):
        """Unpack data to a given type."""
        self._data = data
        super().unpack(self._data)

    @property
    def value(self) -> str:
        """Return data value."""
        value = ""
        offset = 0
        if offset in self._data:
            while not self._data[offset] == 0:
                value += chr(self._data[offset])
                offset += 1

        return value

    @property
    def size(self) -> int:
        """Return data length."""
        return len(self.value) + 1


DATA_TYPES: Tuple[Type[DataType], ...] = (
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
