"""Contains tests for the utility functions."""

import asyncio
from unittest.mock import Mock, patch

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


@patch("asyncio.wait_for", side_effect=("test", asyncio.TimeoutError))
async def test_timeout(mock_wait_for) -> None:
    """Test a timeout decorator."""
    # Mock function to pass to the decorator.
    mock_func = Mock()
    mock_func.return_value = "test"

    # Call the decorator.
    timeout_decorator = utils.timeout(10)
    wrapper = timeout_decorator(mock_func)
    result = await wrapper("test_arg", kwarg="test_kwarg")
    assert result == "test"
    mock_wait_for.assert_awaited_once_with(mock_func.return_value, timeout=10)
    mock_func.assert_called_once_with("test_arg", kwarg="test_kwarg")

    # Test behavior when a timeout occurs.
    mock_func = Mock()
    mock_func.return_value = "test"
    decorator = utils.timeout(10)
    wrapper = decorator(mock_func)
    with pytest.raises(asyncio.TimeoutError):
        await wrapper("test_arg", kwarg="test_kwarg")
