"""Contains tests for utility functions."""

from pyplumio import util


def test_crc() -> None:
    """Test CRC checksum calculation."""
    assert util.crc(b"\x68\x0a\x00\x00\x56\x30\x05\x40") == 0x41


def test_unpack_ushort() -> None:
    """Test unpacking unsigned short."""
    assert util.unpack_ushort(b"\x0a\x00") == 10


def test_ip4_to_bytes() -> None:
    """Test conversion from IPv4 to bytes."""
    assert util.ip4_to_bytes("127.0.0.1") == b"\x7f\x00\x00\x01"


def test_ip4_from_bytes() -> None:
    """Test conversion from bytes to IPv4."""
    assert util.ip4_from_bytes(b"\x7f\x00\x00\x01") == "127.0.0.1"


def test_ip6_from_bytes() -> None:
    """Test conversion from IPv6 to bytes."""
    assert (
        util.ip6_from_bytes(
            b"\xfe\xed\xde\xad\xbe\xef\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01"
        )
        == "feed:dead:beef::1"
    )


def test_ip6_to_bytes() -> None:
    """Test conversion from bytes to IPv6."""
    assert (
        util.ip6_to_bytes("feed:dead:beef::1")
        == b"\xfe\xed\xde\xad\xbe\xef\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01"
    )


def test_to_camelcase() -> None:
    """Test string to camelcase converter."""
    assert util.to_camelcase("make_love_not_war") == "MakeLoveNotWar"
    assert (
        util.to_camelcase("make_love_not_war", overrides={"love": "LOVE", "not": "not"})
        == "MakeLOVEnotWar"
    )
