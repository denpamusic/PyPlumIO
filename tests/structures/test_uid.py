"""Test PyPlumIO uid structure."""

from pyplumio.structures import uid

_message = bytearray.fromhex("0B001600110D3833383655395A")


def test_from_bytes() -> None:
    """Test conversion from bytes."""
    data, offset = uid.from_bytes(_message)
    assert data == "D251PAKR3GCPZ1K8G05G0"
    assert offset == 12


def test_uid_stamp() -> None:
    """Test generating uid stamp."""
    uid_bytes = b"\x00\x16\x00\x11\x0D\x38\x33\x38\x36\x55\x39".decode()
    assert uid.uid_stamp(uid_bytes) == "\x14\xD1"


def test_uid_5bits_to_char() -> None:
    """Test conversion of integers to uid."""
    numbers = (
        0,
        16,
        5,
        0,
        16,
        8,
        20,
        1,
        24,
        25,
        12,
        16,
        3,
        27,
        20,
        10,
        25,
        1,
        5,
        2,
        13,
    )
    assert (
        "".join([uid.uid_5bits_to_char(x) for x in numbers]) == "0G50G8K1ZPCG3RKAP152D"
    )


def test_uid_5bits_to_char_with_out_of_range() -> None:
    """Test conversion from integers to uid with out of range values."""
    numbers = (33, -1)
    assert "".join([uid.uid_5bits_to_char(x) for x in numbers]) == "##"
