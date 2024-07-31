"""Contains data type helper classes."""

from __future__ import annotations

from abc import ABC, abstractmethod
import socket
import struct
from typing import Any, ClassVar, Final, TypeVar


class DataType(ABC):
    """Represents a base data type."""

    __slots__ = ("_value", "_size")

    _value: Any
    _size: int

    def __init__(self, value: Any = None):
        """Initialize a new data type."""
        self._value = value
        self._size = 0

    def __repr__(self) -> str:
        """Return serializable string representation of the class."""
        return f"{self.__class__.__name__}(value={self._value})"

    def __eq__(self, other: object) -> bool:
        """Compare if this data type is equal to other."""
        if isinstance(other, DataType):
            return bool(self._value == other._value)

        return bool(self._value == other)

    def _slice_data(self, data: bytes) -> bytes:
        """Slice the data to data type size."""
        return data[: self.size] if self.size is not None else data

    @classmethod
    def from_bytes(cls: type[DataTypeT], data: bytes, offset: int = 0) -> DataTypeT:
        """Initialize a new data type from bytes."""
        data_type = cls()
        data_type.unpack(data[offset:])
        return data_type

    def to_bytes(self) -> bytes:
        """Convert data type to bytes."""
        return self.pack()

    @property
    def value(self) -> Any:
        """Return the data type value."""
        return self._value

    @property
    def size(self) -> int:
        """Return the data type size."""
        return self._size

    @abstractmethod
    def pack(self) -> bytes:
        """Pack the data."""

    @abstractmethod
    def unpack(self, data: bytes) -> None:
        """Unpack the data."""


DataTypeT = TypeVar("DataTypeT", bound=DataType)


class Undefined(DataType):
    """Represents an undefined."""

    __slots__ = ()

    def pack(self) -> bytes:
        """Pack the data."""
        return b""

    def unpack(self, _: bytes) -> None:
        """Unpack the data."""
        self._value = None


BITARRAY_LAST_INDEX: Final = 7


class BitArray(DataType):
    """Represents a bit array."""

    __slots__ = ("_index",)

    _index: int

    def __init__(self, value: Any = None, index: int = 0):
        """Initialize a new bit array."""
        super().__init__(value)
        self._index = index

    def __repr__(self) -> str:
        """Return serializable string representation of the class."""
        return f"{self.__class__.__name__}(value={self._value}, index={self._index})"

    def next(self, index: int = 0) -> int:
        """Set current bit and return the next index in the bit array."""
        self._index = index
        return 0 if self._index == BITARRAY_LAST_INDEX else self._index + 1

    def pack(self) -> bytes:
        """Pack the data."""
        return UnsignedChar(self._value).to_bytes()

    def unpack(self, data: bytes) -> None:
        """Unpack the data."""
        self._value = UnsignedChar.from_bytes(data[:1]).value

    @property
    def value(self) -> bool | None:
        """Return the data type value."""
        return None if self._value is None else bool(self._value & (1 << self._index))

    @property
    def size(self) -> int:
        """Return the data type size."""
        return 1 if self._index == BITARRAY_LAST_INDEX else 0


class IPv4(DataType):
    """Represents an IPv4 address."""

    __slots__ = ()

    @property
    def size(self) -> int:
        """Return the data type size."""
        return 4

    def pack(self) -> bytes:
        """Pack the data."""
        return socket.inet_aton(self.value)

    def unpack(self, data: bytes) -> None:
        """Unpack the data."""
        self._value = socket.inet_ntoa(self._slice_data(data))


class IPv6(DataType):
    """Represents an IPv6 address."""

    __slots__ = ()

    @property
    def size(self) -> int:
        """Return a data type size."""
        return 16

    def pack(self) -> bytes:
        """Pack the data."""
        return socket.inet_pton(socket.AF_INET6, self.value)

    def unpack(self, data: bytes) -> None:
        """Unpack the data."""
        self._value = socket.inet_ntop(socket.AF_INET6, self._slice_data(data))


class String(DataType):
    """Represents a null terminated string."""

    __slots__ = ()

    def __init__(self, value: Any = ""):
        """Initialize a new null terminated string data type."""
        super().__init__(value)
        self._size = len(self.value) + 1

    def pack(self) -> bytes:
        """Pack the data."""
        value: str = self.value
        return value.encode() + b"\0"

    def unpack(self, data: bytes) -> None:
        """Unpack the data."""
        self._value = data.split(b"\0", 1)[0].decode("utf-8", "replace")
        self._size = len(self.value) + 1


class VarBytes(DataType):
    """Represents a variable length bytes."""

    __slots__ = ()

    def __init__(self, value: Any = b""):
        """Initialize a new variable length bytes data type."""
        super().__init__(value)
        self._size = len(value) + 1

    def pack(self) -> bytes:
        """Pack the data."""
        value: bytes = self.value
        return UnsignedChar(self.size - 1).to_bytes() + value

    def unpack(self, data: bytes) -> None:
        """Unpack the data."""
        self._size = data[0] + 1
        self._value = data[1 : self.size]


class VarString(VarBytes):
    """Represents a variable length string."""

    __slots__ = ()

    def pack(self) -> bytes:
        """Pack the data."""
        value: str = self.value
        return UnsignedChar(self.size - 1).to_bytes() + value.encode()

    def unpack(self, data: bytes) -> None:
        """Unpack the data."""
        super().unpack(data)
        self._value = self.value.decode()


class BuiltInDataType(DataType, ABC):
    """Represents a data type that is supported by the struct module."""

    __slots__ = ()

    _struct: ClassVar[struct.Struct]

    def pack(self) -> bytes:
        """Pack the data."""
        return self._struct.pack(self.value)

    def unpack(self, data: bytes) -> None:
        """Unpack the data."""
        self._value = self._struct.unpack_from(data)[0]

    @property
    def size(self) -> int:
        """Return a data type size."""
        return self._struct.size


class SignedChar(BuiltInDataType):
    """Represents a signed char."""

    __slots__ = ()

    _struct: ClassVar[struct.Struct] = struct.Struct("<b")


class UnsignedChar(BuiltInDataType):
    """Represents an unsigned char."""

    __slots__ = ()

    _struct: ClassVar[struct.Struct] = struct.Struct("<B")


class Short(BuiltInDataType):
    """Represents a 16 bit integer."""

    __slots__ = ()

    _struct: ClassVar[struct.Struct] = struct.Struct("<h")


class UnsignedShort(BuiltInDataType):
    """Represents an unsigned 16 bit integer."""

    __slots__ = ()

    _struct: ClassVar[struct.Struct] = struct.Struct("<H")


class Int(BuiltInDataType):
    """Represents a 32 bit integer."""

    __slots__ = ()

    _struct: ClassVar[struct.Struct] = struct.Struct("<i")


class UnsignedInt(BuiltInDataType):
    """Represents a unsigned 32 bit integer."""

    __slots__ = ()

    _struct: ClassVar[struct.Struct] = struct.Struct("<I")


class Float(BuiltInDataType):
    """Represents a float."""

    __slots__ = ()

    _struct: ClassVar[struct.Struct] = struct.Struct("<f")


class Double(BuiltInDataType):
    """Represents a double."""

    __slots__ = ()

    _struct: ClassVar[struct.Struct] = struct.Struct("<d")


class Int64(BuiltInDataType):
    """Represents a 64 bit signed integer."""

    __slots__ = ()

    _struct: ClassVar[struct.Struct] = struct.Struct("<q")


class UInt64(BuiltInDataType):
    """Represents a 64 bit unsigned integer."""

    __slots__ = ()
    _struct: ClassVar[struct.Struct] = struct.Struct("<Q")


# The regdata type map links data type classes to their
# respective type ids in the regulator data schema.
DATA_TYPES: tuple[type[DataType], ...] = (
    Undefined,
    SignedChar,
    Short,
    Int,
    UnsignedChar,
    UnsignedShort,
    UnsignedInt,
    Float,
    Undefined,
    Double,
    BitArray,
    String,
    String,
    Int64,
    UInt64,
    IPv4,
    IPv6,
)
