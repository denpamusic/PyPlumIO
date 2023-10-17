"""Contains tests for utility functions."""

from pyplumio import util


def test_crc() -> None:
    """Test CRC checksum calculation."""
    assert util.crc(b"\x68\x0a\x00\x00\x56\x30\x05\x40") == 0x41


def test_to_camelcase() -> None:
    """Test string to camelcase converter."""
    assert util.to_camelcase("make_love_not_war") == "MakeLoveNotWar"
    assert (
        util.to_camelcase("make_love_not_war", overrides={"love": "LOVE", "not": "not"})
        == "MakeLOVEnotWar"
    )
