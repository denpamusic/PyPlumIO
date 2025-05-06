"""Contains tests for the utility functions."""

import pytest

from pyplumio import utils
from tests.conftest import RAISES


@pytest.mark.parametrize(
    ("input_value", "overrides", "expected"),
    [
        ("make_love_not_war", None, "MakeLoveNotWar"),
        ("make_love_not_war", {"love": "LOVE", "not": "not"}, "MakeLOVEnotWar"),
        ("miku_love_forever", None, "MikuLoveForever"),
        (
            "miku_love_forever",
            {"love": "LOVE", "forever": "Forever"},
            "MikuLOVEForever",
        ),
    ],
)
def test_to_camelcase(input_value, overrides, expected) -> None:
    """Test string to camelcase converter."""
    assert utils.to_camelcase(input_value, overrides=overrides) == expected


@pytest.mark.parametrize(
    ("dct", "defaults", "expected"),
    [
        ({"foo": "bar"}, {"baz": "foobar"}, {"foo": "bar", "baz": "foobar"}),
        ({}, {"baz": "foobar"}, {"baz": "foobar"}),
    ],
)
def test_ensure_dict(dct, defaults, expected) -> None:
    """Test ensure dictionary."""
    assert utils.ensure_dict(dct, defaults) == expected


@pytest.mark.parametrize(
    ("input_value", "divisor", "expected"),
    [
        (10.0, 0.2, True),
        (0.0, 1.0, True),
        (10.0, 3.0, False),
        (39.0, 13.0, True),
        (39.0, 7.0, False),
        (39.0, 1.0, True),
        (39.0, 39.0, True),
        (39.0, 0.0, RAISES),
    ],
)
def test_is_divisible(input_value, divisor, expected) -> None:
    """Test divisibility check."""
    if expected == RAISES:
        with pytest.raises(ValueError, match="Division by zero is not allowed."):
            utils.is_divisible(input_value, divisor)
    else:
        assert utils.is_divisible(input_value, divisor) == expected
