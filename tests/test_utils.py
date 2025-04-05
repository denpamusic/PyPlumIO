"""Contains tests for the utility functions."""

import pytest

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


def test_is_divisible() -> None:
    """Test divisibility check."""
    assert utils.is_divisible(10.0, 0.2)
    assert utils.is_divisible(0.0, 1.0)
    assert not utils.is_divisible(10.0, 3.0)

    with pytest.raises(ValueError, match="Division by zero is not allowed."):
        utils.is_divisible(10.0, 0.0)
