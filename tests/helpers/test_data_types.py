"""Contains tests for the data type helper classes."""

import pytest

from pyplumio.helpers import data_types


@pytest.mark.parametrize(
    "one, another",
    [
        (
            data_types.SignedChar.from_bytes(bytearray([0x16])),
            data_types.SignedChar.from_bytes(bytearray([0x16])),
        ),
        (
            data_types.SignedChar.from_bytes(bytearray([0x16])),
            22,
        ),
    ],
)
def test_type_eq(one, another):
    """Test a generic type comparison."""
    assert one == another


def test_undefined() -> None:
    """Test an undefined data type."""
    buffer = bytearray()
    data_type = data_types.Undefined.from_bytes(buffer)
    assert data_type.value is None
    assert data_type.size == 0
    assert not data_type.to_bytes()
    assert repr(data_type) == "Undefined(value=None)"
    assert data_type == data_types.Undefined.from_bytes(buffer)


def test_signed_char() -> None:
    """Test a signed char data type."""
    buffer = bytearray([0x16])
    data_type = data_types.SignedChar.from_bytes(buffer)
    assert data_type.value == 22
    assert data_type.size == 1
    assert data_type.to_bytes() == buffer
    assert repr(data_type) == "SignedChar(value=22)"
    assert data_type == data_types.SignedChar.from_bytes(buffer)
    assert data_type == 22


def test_short() -> None:
    """Test a short data type."""
    buffer = bytearray([0xEC, 0xFF])
    data_type = data_types.Short.from_bytes(buffer)
    assert data_type.value == -20
    assert data_type.size == 2
    assert data_type.to_bytes() == buffer
    assert repr(data_type) == "Short(value=-20)"
    assert data_type == data_types.Short.from_bytes(buffer)
    assert data_type == -20


def test_int() -> None:
    """Test an integer data type."""
    buffer = bytearray([0x01, 0x9A, 0xFF, 0xFF])
    data_type = data_types.Int.from_bytes(buffer)
    assert data_type.value == -26111
    assert data_type.size == 4
    assert data_type.to_bytes() == buffer
    assert repr(data_type) == "Int(value=-26111)"
    assert data_type == data_types.Int.from_bytes(buffer)
    assert data_type == -26111


def test_unsigned_char() -> None:
    """Test an signed char data type."""
    buffer = bytearray([0x3])
    data_type = data_types.UnsignedChar.from_bytes(buffer)
    assert data_type.value == 3
    assert data_type.size == 1
    assert data_type.to_bytes() == buffer
    assert repr(data_type) == "UnsignedChar(value=3)"
    assert data_type == data_types.UnsignedChar.from_bytes(buffer)
    assert data_type == 3


def test_ushort() -> None:
    """Test an unsigned short data type."""
    buffer = bytearray([0x2A, 0x01])
    data_type = data_types.UnsignedShort.from_bytes(buffer)
    assert data_type.value == 298
    assert data_type.size == 2
    assert data_type.to_bytes() == buffer
    assert repr(data_type) == "UnsignedShort(value=298)"
    assert data_type == data_types.UnsignedShort.from_bytes(buffer)
    assert data_type == 298


def test_uint() -> None:
    """Test an unsigned integer data type."""
    buffer = bytearray([0x9A, 0x3F, 0x0, 0x0])
    data_type = data_types.UnsignedInt.from_bytes(buffer)
    assert data_type.value == 16282
    assert data_type.size == 4
    assert data_type.to_bytes() == buffer
    assert repr(data_type) == "UnsignedInt(value=16282)"
    assert data_type == data_types.UnsignedInt.from_bytes(buffer)
    assert data_type == 16282


def test_float() -> None:
    """Test a float data type."""
    buffer = bytearray([0x0, 0x0, 0x40, 0x41])
    data_type = data_types.Float.from_bytes(buffer)
    assert data_type.value == 12.0
    assert data_type.size == 4
    assert data_type.to_bytes() == buffer
    assert repr(data_type) == "Float(value=12.0)"
    assert data_type == data_types.Float.from_bytes(buffer)
    assert data_type == 12.0


def test_double() -> None:
    """Test a double data type."""
    buffer = bytearray([0x3D, 0x0A, 0xD7, 0xA3, 0x70, 0x3D, 0x28, 0x40])
    data_type = data_types.Double.from_bytes(buffer)
    assert data_type.value == 12.12
    assert data_type.size == 8
    assert data_type.to_bytes() == buffer
    assert repr(data_type) == "Double(value=12.12)"
    assert data_type == data_types.Double.from_bytes(buffer)
    assert data_type == 12.12


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
    assert data_type == data_types.BitArray.from_bytes(buffer)
    assert data_type == 85


def test_int64() -> None:
    """Test a 64 bit integer data type."""
    buffer = bytearray([0xFF, 0xFF, 0xFF, 0xFF, 0xF8, 0xA4, 0x32, 0xEB])
    data_type = data_types.Int64.from_bytes(buffer)
    assert data_type.value == -1498954336607141889
    assert data_type.size == 8
    assert data_type.to_bytes() == buffer
    assert repr(data_type) == "Int64(value=-1498954336607141889)"
    assert data_type == data_types.Int64.from_bytes(buffer)
    assert data_type == -1498954336607141889


def test_uint64() -> None:
    """Test a unsigned 64 bit integer data type."""
    buffer = bytearray([0x45, 0x49, 0x50, 0x51, 0x52, 0x53, 0x54, 0x55])
    data_type = data_types.UInt64.from_bytes(buffer)
    assert data_type.value == 6148631004284209477
    assert data_type.size == 8
    assert data_type.to_bytes() == buffer
    assert repr(data_type) == "UInt64(value=6148631004284209477)"
    assert data_type == data_types.UInt64.from_bytes(buffer)
    assert data_type == 6148631004284209477


def test_ipv4() -> None:
    """Test an IPv4 data type."""
    buffer = bytearray([0x7F, 0x00, 0x00, 0x01])
    data_type = data_types.IPv4.from_bytes(buffer)
    assert data_type.value == "127.0.0.1"
    assert data_type.size == 4
    assert data_type.to_bytes() == buffer
    assert repr(data_type) == "IPv4(value=127.0.0.1)"
    assert data_type == data_types.IPv4.from_bytes(buffer)
    assert data_type == "127.0.0.1"


def test_ipv6() -> None:
    """Test an IPv6 data type."""
    buffer = bytearray(
        [
            0xFE,
            0xED,
            0xDE,
            0xAD,
            0xBE,
            0xEF,
            0x0,
            0x0,
            0x0,
            0x0,
            0x0,
            0x0,
            0x0,
            0x0,
            0x0,
            0x1,
        ]
    )

    data_type = data_types.IPv6.from_bytes(buffer)
    assert data_type.value == "feed:dead:beef::1"
    assert data_type.size == 16
    assert data_type.to_bytes() == buffer
    assert repr(data_type) == "IPv6(value=feed:dead:beef::1)"
    assert data_type == data_types.IPv6.from_bytes(buffer)
    assert data_type == "feed:dead:beef::1"


def test_string() -> None:
    """Test a string data type."""
    buffer = b"test\x00"
    data_type = data_types.String.from_bytes(buffer)
    assert data_type.value == "test"
    assert data_type.size == 5
    assert data_type.to_bytes() == buffer
    assert repr(data_type) == "String(value=test)"
    assert data_type == data_types.String.from_bytes(buffer)
    assert data_type == "test"


def test_var_bytes() -> None:
    """Test a variable bytes data type."""
    buffer = b"\x04\xDE\xAD\xBE\xEF"
    data_type = data_types.VarBytes.from_bytes(buffer)
    assert data_type.value == bytearray([0xDE, 0xAD, 0xBE, 0xEF])
    assert data_type.size == 5
    assert data_type.to_bytes() == buffer
    assert repr(data_type) == "VarBytes(value=b'\\xde\\xad\\xbe\\xef')"
    assert data_type == data_types.VarBytes.from_bytes(buffer)
    assert data_type == bytearray([0xDE, 0xAD, 0xBE, 0xEF])


def test_var_string() -> None:
    """Test a variable string data type."""
    buffer = b"\x04test"
    data_type = data_types.VarString.from_bytes(buffer)
    assert data_type.value == "test"
    assert data_type.size == 5
    assert data_type.to_bytes() == buffer
    assert repr(data_type) == "VarString(value=test)"
    assert data_type == data_types.VarString.from_bytes(buffer)
    assert data_type == "test"
