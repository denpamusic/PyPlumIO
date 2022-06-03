"""Test PyPlumIO data types."""

from pyplumio import data_types


def test_type_repr():
    """Test serializable type representation."""
    type = data_types.SignedChar(bytearray([0x16]))
    assert (
        repr(type)
        == """SignedChar(
    data = bytearray(b'\\x16'),
    size = 1
)
""".strip()
    )


def test_equality():
    """Test type equality check."""
    type = data_types.SignedChar(bytearray([0x16]))
    other = data_types.SignedChar(bytearray([0x16]))
    assert type == other


def test_type_unpack() -> None:
    """Test generic type unpack."""
    type = data_types.SignedChar()
    type.unpack(bytearray([0x16]))
    assert type.value == 22
    assert type.size == 1


def test_undefined0() -> None:
    """Test undefined0 type."""
    type = data_types.Undefined0(bytearray([0x0]))
    assert type.value is None
    assert type.size == 0


def test_signed_char() -> None:
    """Test signed char type."""
    type = data_types.SignedChar(bytearray([0x16]))
    assert type.value == 22
    assert type.size == 1


def test_short() -> None:
    """Test short type."""
    type = data_types.Short(bytearray([0xEC, 0xFF]))
    assert type.value == -20
    assert type.size == 2


def test_int() -> None:
    """Test integer type."""
    type = data_types.Int(bytearray([0x01, 0x9A, 0xFF, 0xFF]))
    assert type.value == -26111
    assert type.size == 4


def test_byte() -> None:
    """Test byte type."""
    type = data_types.Byte(bytearray([0x3]))
    assert type.value == 3
    assert type.size == 1


def test_ushort() -> None:
    """Test unsigned short type."""
    type = data_types.UnsignedShort(bytearray([0x2A, 0x01]))
    assert type.value == 298
    assert type.size == 2


def test_uint() -> None:
    """Test unsigned integer type."""
    type = data_types.UnsignedInt(bytearray([0x9A, 0x3F, 0x0, 0x0]))
    assert type.value == 16282
    assert type.size == 4


def test_float() -> None:
    """Test float type."""
    type = data_types.Float(bytearray([0x0, 0x0, 0x40, 0x41]))
    assert type.value == 12.0
    assert type.size == 4


def test_undefined8() -> None:
    """Test undefined8 type."""
    type = data_types.Undefined8(bytearray([0x0]))
    assert type.value is None
    assert type.size == 0


def test_double() -> None:
    """Test double type."""
    type = data_types.Double(
        bytearray([0x3D, 0x0A, 0xD7, 0xA3, 0x70, 0x3D, 0x28, 0x40])
    )
    assert type.value == 12.12
    assert type.size == 8


def test_boolean() -> None:
    """Test boolean type."""
    type = data_types.Boolean(bytearray([0x55]))
    for index, value in enumerate([1, 0, 1, 0, 1, 0, 1, 0]):
        next = type.index(index)
        assert type.value == bool(value)
        if index < 7:
            assert next == index + 1
            assert type.size == 0
        else:
            assert next == 0
            assert type.size == 1


def test_boolean_unpack() -> None:
    """Test boolean unpack."""
    type = data_types.Boolean()
    type.unpack(bytearray([0x55]))
    assert type.value
    assert type.size == 0


def test_int64() -> None:
    """Test 64 bit integer type."""
    type = data_types.Int64(bytearray([0xFF, 0xFF, 0xFF, 0xFF, 0xF8, 0xA4, 0x32, 0xEB]))
    assert type.value == -1498954336607141889
    assert type.size == 8


def test_uint64() -> None:
    """Test unsigned 64 bit integer type."""
    type = data_types.UInt64(
        bytearray([0x45, 0x49, 0x50, 0x51, 0x52, 0x53, 0x54, 0x55])
    )
    assert type.value == 6148631004284209477
    assert type.size == 8


def test_ipv4() -> None:
    """Test IPv4 type."""
    type = data_types.IPv4(bytearray([0x7F, 0x00, 0x00, 0x01]))
    assert type.value == "127.0.0.1"
    assert type.size == 4


def test_ipv6() -> None:
    """Test IPv6 type."""
    type = data_types.IPv6(
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
    assert type.value == "feed:dead:beef::1"
    assert type.size == 16


def test_string() -> None:
    """Test string type."""
    type = data_types.String(b"test\x00")
    assert type.value == "test"
    assert type.size == 5


def test_string_unpack() -> None:
    """Test string unpack."""
    type = data_types.String()
    type.unpack(b"test\x00")
    assert type.value == "test"
    assert type.size == 5
