"""Contains tests for the utility functions."""

from pyplumio import utils


def test_to_camelcase() -> None:
    """Test string to camelcase converter."""
    assert utils.to_camelcase("make_love_not_war") == "MakeLoveNotWar"
    assert (
        utils.to_camelcase(
            "make_love_not_war", overrides={"love": "LOVE", "not": "not"}
        )
        == "MakeLOVEnotWar"
    )


def test_ensure_dict() -> None:
    """Test ensure dictionary."""
    assert utils.ensure_dict({"foo": "bar"}, {"baz": "foobar"}) == {
        "foo": "bar",
        "baz": "foobar",
    }
