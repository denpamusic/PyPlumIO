"""Contains tests for utility functions."""

from pyplumio import util


def test_to_camelcase() -> None:
    """Test string to camelcase converter."""
    assert util.to_camelcase("make_love_not_war") == "MakeLoveNotWar"
    assert (
        util.to_camelcase("make_love_not_war", overrides={"love": "LOVE", "not": "not"})
        == "MakeLOVEnotWar"
    )
