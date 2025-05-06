"""Contains tests for the data type helper classes."""

from math import isclose
from typing import Any

import pytest

from pyplumio import data_types
from tests.conftest import DEFAULT_TOLERANCE, UNDEFINED


@pytest.mark.parametrize(
    ("one", "another"),
    [
        (
            data_types.SignedChar.from_bytes(bytearray([0x16])),
            data_types.SignedChar.from_bytes(bytearray([0x16])),
        ),
        (
            data_types.SignedChar.from_bytes(bytearray([0x16])),
            22,
        ),
        (
            data_types.SignedChar(),
            data_types.SignedChar(),
        ),
        (
            data_types.SignedChar(),
            "not_implemented",
        ),
    ],
)
def test_type_eq(one, another):
    """Test a generic type comparison."""
    if another != "not_implemented":
        assert one == another
    else:
        assert one.__eq__(another) is NotImplemented


@pytest.mark.parametrize(
    ("cls", "buffer", "expected"),
    [
        (data_types.Undefined, bytearray(), None),
        (data_types.SignedChar, bytearray.fromhex("16"), 22),
        (data_types.Short, bytearray.fromhex("ECFF"), -20),
        (data_types.Int, bytearray.fromhex("019AFFFF"), -26111),
        (data_types.UnsignedChar, bytearray.fromhex("03"), 3),
        (data_types.UnsignedShort, bytearray.fromhex("2A01"), 298),
        (data_types.UnsignedInt, bytearray.fromhex("9A3F0000"), 16282),
        (data_types.Float, bytearray.fromhex("00004041"), 12.0),
        (data_types.Double, bytearray.fromhex("3D0AD7A3703D2840"), 12.12),
        (data_types.Int64, bytearray.fromhex("FFFFFFFFF8A432EB"), -1498954336607141889),
        (data_types.UInt64, bytearray.fromhex("4549505152535455"), 6148631004284209477),
        (data_types.IPv4, bytearray.fromhex("7F000001"), "127.0.0.1"),
        (
            data_types.IPv6,
            bytearray.fromhex("FEEDDEADBEEF00000000000000000001"),
            "feed:dead:beef::1",
        ),
        (data_types.String, b"test\x00", "test"),
        (data_types.VarBytes, b"\x04\xde\xad\xbe\xef", b"\xde\xad\xbe\xef"),
        (data_types.VarString, b"\x04test", "test"),
    ],
)
def test_data_type(
    cls: type[data_types.DataType], buffer: bytes, expected: Any
) -> None:
    """Test data types."""
    data_type = cls.from_bytes(buffer)
    if isinstance(expected, float):
        assert isclose(data_type.value, expected, rel_tol=DEFAULT_TOLERANCE)
    else:
        assert data_type.value == expected
        assert data_type == expected

    assert data_type.size == len(buffer)
    assert data_type.to_bytes() == buffer
    assert repr(data_type) == f"{cls.__qualname__}(value={expected})"

    if not isinstance(
        data_type, (data_types.String, data_types.VarBytes, data_types.VarString)
    ):
        assert repr(cls()) == f"{cls.__qualname__}()"
        assert cls().__eq__(UNDEFINED) is NotImplemented


def test_bitarray() -> None:
    """Test a bit array data type."""
    buffer = bytearray([0x55])
    data_type = data_types.BitArray.from_bytes(buffer)
    for index, value in enumerate([1, 0, 1, 0, 1, 0, 1, 0]):
        next_bit = data_type.next(index)
        assert data_type.value == bool(value)
        if index < 7:
            assert next_bit == index + 1
            assert data_type.size == 0
        else:
            assert next_bit == 0
            assert data_type.size == 1

    assert data_type.to_bytes() == buffer
    assert repr(data_type) == "BitArray(value=85, index=7)"
    assert repr(data_types.BitArray()) == "BitArray(index=0)"
    assert data_type == data_types.BitArray.from_bytes(buffer)
    assert data_type == 85
    assert data_types.BitArray().pack() == b""


def test_bitarray_no_value() -> None:
    """Test a bit array data type with no value."""
    with pytest.raises(ValueError):
        data_types.BitArray().value


def test_string_unknown_char() -> None:
    """Test string with unknown unicode char."""
    assert data_types.String.from_bytes(b"test\xd8\x00").value == "test�"
