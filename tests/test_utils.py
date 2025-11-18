"""Contains tests for the utility functions."""

import asyncio
from typing import Literal
from unittest.mock import Mock, patch

import pytest

from pyplumio import utils
from pyplumio.frames import Frame, Request, Response
from pyplumio.frames.messages import RegulatorDataMessage
from pyplumio.frames.requests import StopMasterRequest
from pyplumio.frames.responses import UIDResponse
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


@pytest.mark.parametrize(
    ("input_value", "expected"),
    [
        ("10110101", 181),
        ("11111111", 255),
        ("00000000", 0),
        ("1000", 8),
        ("10000", 16),
        ("100000001", RAISES),
    ],
)
def test_join_bits(input_value: str, expected: int | Literal["raises"]) -> None:
    """Test joining bits into a single byte."""
    bits = [bool(int(x)) for x in input_value]
    if expected == RAISES:
        with pytest.raises(ValueError, match="must not exceed 8"):
            utils.join_bits(bits)
    else:
        assert utils.join_bits(bits) == expected


def test_join_bits_with_bool() -> None:
    """Test joining bits into a single byte with bools."""
    bits = (True, False, False, True)
    assert utils.join_bits(bits) == 9


@pytest.mark.parametrize(
    ("input_value", "expected"),
    [
        (4, [False, False, False, False, False, True, False, False]),
        (128, [True, False, False, False, False, False, False, False]),
        (0, [False, False, False, False, False, False, False, False]),
        (255, [True, True, True, True, True, True, True, True]),
        (-128, RAISES),
        (268, RAISES),
    ],
)
def test_split_byte(input_value: int, expected: list[bool] | Literal["raises"]) -> None:
    """Test splitting a byte into list of bits."""
    if expected == RAISES:
        with pytest.raises(ValueError, match="between 0 and 255"):
            utils.split_byte(input_value)
    else:
        assert utils.split_byte(input_value) == expected


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


@pytest.mark.parametrize(
    ("path", "base", "expected", "error_pattern"),
    [
        ("frames.requests.StopMasterRequest", Request, StopMasterRequest, None),
        ("frames.responses.UIDResponse", Response, UIDResponse, None),
        ("frames.messages.RegulatorDataMessage", Frame, RegulatorDataMessage, None),
        ("frames.responses.UIDResponse", Request, RAISES, "Expected instance"),
        ("frames.requests.NonExistent", Request, RAISES, "no attribute"),
        ("frames.request.StopMasterRequest", Request, RAISES, "No module"),
    ],
)
async def test_create_instance(
    path: str,
    base: type,
    expected: type | Literal["raises"],
    error_pattern: str | None,
) -> None:
    """Test creating an instance of class."""
    if expected == RAISES:
        with pytest.raises(
            (TypeError, AttributeError, ModuleNotFoundError), match=error_pattern
        ):
            await utils.create_instance(path, cls=base)
    else:
        assert isinstance(await utils.create_instance(path, cls=base), expected)
