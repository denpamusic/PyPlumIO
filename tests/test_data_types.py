"""Contains tests for DataType classes."""

from pyplumio.helpers import data_types


def test_type_repr():
    """Test serializable type representation."""
    data_type_repr = repr(data_types.SignedChar(bytearray([0x16])))
    assert "SignedChar" in data_type_repr
    assert "data=bytearray(b'\\x16')" in data_type_repr
    assert "size=1" in data_type_repr


def test_equality():
    """Test type equality check."""
    data_type = data_types.SignedChar(bytearray([0x16]))
    other = data_types.SignedChar(bytearray([0x16]))
    assert data_type == other


def test_type_unpack() -> None:
    """Test generic type unpack."""
    data_type = data_types.SignedChar()
    data_type.unpack(bytearray([0x16]))
    assert data_type.value == 22
    assert data_type.size == 1


def test_undefined0() -> None:
    """Test undefined0 data_type."""
    data_type = data_types.Undefined0(bytearray([0x0]))
    assert data_type.value is None
    assert data_type.size == 0


def test_signed_char() -> None:
    """Test signed char data_type."""
    data_type = data_types.SignedChar(bytearray([0x16]))
    assert data_type.value == 22
    assert data_type.size == 1


def test_short() -> None:
    """Test short data_type."""
    data_type = data_types.Short(bytearray([0xEC, 0xFF]))
    assert data_type.value == -20
    assert data_type.size == 2


def test_int() -> None:
    """Test integer data_type."""
    data_type = data_types.Int(bytearray([0x01, 0x9A, 0xFF, 0xFF]))
    assert data_type.value == -26111
    assert data_type.size == 4


def test_byte() -> None:
    """Test byte data_type."""
    data_type = data_types.Byte(bytearray([0x3]))
    assert data_type.value == 3
    assert data_type.size == 1


def test_ushort() -> None:
    """Test unsigned short data_type."""
    data_type = data_types.UnsignedShort(bytearray([0x2A, 0x01]))
    assert data_type.value == 298
    assert data_type.size == 2


def test_uint() -> None:
    """Test unsigned integer data_type."""
    data_type = data_types.UnsignedInt(bytearray([0x9A, 0x3F, 0x0, 0x0]))
    assert data_type.value == 16282
    assert data_type.size == 4


def test_float() -> None:
    """Test float data_type."""
    data_type = data_types.Float(bytearray([0x0, 0x0, 0x40, 0x41]))
    assert data_type.value == 12.0
    assert data_type.size == 4


def test_undefined8() -> None:
    """Test undefined8 data_type."""
    data_type = data_types.Undefined8(bytearray([0x0]))
    assert data_type.value is None
    assert data_type.size == 0


def test_double() -> None:
    """Test double data_type."""
    data_type = data_types.Double(
        bytearray([0x3D, 0x0A, 0xD7, 0xA3, 0x70, 0x3D, 0x28, 0x40])
    )
    assert data_type.value == 12.12
    assert data_type.size == 8


def test_boolean() -> None:
    """Test boolean data_type."""
    data_type = data_types.Boolean(bytearray([0x55]))
    for index, value in enumerate([1, 0, 1, 0, 1, 0, 1, 0]):
        next = data_type.index(index)
        assert data_type.value == bool(value)
        if index < 7:
            assert next == index + 1
            assert data_type.size == 0
        else:
            assert next == 0
            assert data_type.size == 1


def test_boolean_unpack() -> None:
    """Test boolean unpack."""
    data_type = data_types.Boolean()
    data_type.unpack(bytearray([0x55]))
    assert data_type.value
    assert data_type.size == 0


def test_int64() -> None:
    """Test 64 bit integer data_type."""
    data_type = data_types.Int64(
        bytearray([0xFF, 0xFF, 0xFF, 0xFF, 0xF8, 0xA4, 0x32, 0xEB])
    )
    assert data_type.value == -1498954336607141889
    assert data_type.size == 8


def test_uint64() -> None:
    """Test unsigned 64 bit integer data_type."""
    data_type = data_types.UInt64(
        bytearray([0x45, 0x49, 0x50, 0x51, 0x52, 0x53, 0x54, 0x55])
    )
    assert data_type.value == 6148631004284209477
    assert data_type.size == 8


def test_ipv4() -> None:
    """Test IPv4 data_type."""
    data_type = data_types.IPv4(bytearray([0x7F, 0x00, 0x00, 0x01]))
    assert data_type.value == "127.0.0.1"
    assert data_type.size == 4


def test_ipv6() -> None:
    """Test IPv6 data_type."""
    data_type = data_types.IPv6(
        bytearray(
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
    )
    assert data_type.value == "feed:dead:beef::1"
    assert data_type.size == 16


def test_string() -> None:
    """Test string data_type."""
    data_type = data_types.String(b"test\x00")
    assert data_type.value == "test"
    assert data_type.size == 5


def test_string_unpack() -> None:
    """Test string unpack."""
    data_type = data_types.String()
    data_type.unpack(b"test\x00")
    assert data_type.value == "test"
    assert data_type.size == 5
