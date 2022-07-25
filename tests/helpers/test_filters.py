"""Contains tests for callback filters."""

from unittest.mock import AsyncMock, patch

import pytest

from pyplumio.helpers.filters import aggregate, debounce, delta, on_change, throttle


async def test_on_change() -> None:
    """Test on change filter."""
    test_callback = AsyncMock()
    wrapped_callback = on_change(test_callback)
    await wrapped_callback(1)
    test_callback.assert_awaited_once_with(1)
    test_callback.reset_mock()

    # Check that callback is not awaited on insignificant change.
    await wrapped_callback(1.01)
    test_callback.assert_not_awaited()

    await wrapped_callback(1.1)
    test_callback.assert_awaited_once_with(1.1)

    # Test equality with callback function and different instance.
    assert test_callback == wrapped_callback
    assert wrapped_callback == on_change(test_callback)
    with pytest.raises(TypeError):
        _ = wrapped_callback == "you shall not pass"


async def test_debounce() -> None:
    """Test debounce filter."""
    test_callback = AsyncMock()
    wrapped_callback = debounce(test_callback, min_calls=3)
    await wrapped_callback(1)
    test_callback.assert_awaited_once_with(1)
    test_callback.reset_mock()

    # Ignore stray "1" and only await callback on a "2".
    await wrapped_callback(2)
    await wrapped_callback(1)
    await wrapped_callback(2)
    await wrapped_callback(2)
    await wrapped_callback(2)
    test_callback.assert_awaited_once_with(2)


@patch("time.time", side_effect=(0, 1, 5, 6))
async def test_throttle(mock_time) -> None:
    """Test throttle filter."""
    test_callback = AsyncMock()
    wrapped_callback = throttle(test_callback, seconds=5)
    await wrapped_callback(1)
    test_callback.assert_awaited_once_with(1)
    test_callback.reset_mock()

    # One second passed.
    await wrapped_callback(2)
    test_callback.assert_not_awaited()

    # Five seconds passed.
    await wrapped_callback(3)
    test_callback.assert_awaited_once_with(3)
    test_callback.reset_mock()

    # Six seconds passed.
    await wrapped_callback(4)
    test_callback.assert_not_awaited()


async def test_delta() -> None:
    """Test delta filter."""
    test_callback = AsyncMock()
    wrapped_callback = delta(test_callback)

    await wrapped_callback(5)
    test_callback.assert_not_awaited()

    await wrapped_callback(3)
    test_callback.assert_awaited_once_with(-2)
    test_callback.reset_mock()

    wrapped_callback = delta(test_callback)
    await wrapped_callback(["foo"])
    test_callback.assert_not_awaited()

    await wrapped_callback(["foo", "bar"])
    test_callback.assert_awaited_once_with(["bar"])


@patch("time.time", side_effect=(0, 0, 1, 5, 6))
async def test_aggregate(mock_time) -> None:
    """Test aggregate filter."""
    test_callback = AsyncMock()
    wrapped_callback = aggregate(test_callback, seconds=5)

    # Zero seconds passed.
    await wrapped_callback(1)
    test_callback.assert_not_awaited()

    # One second passed.
    await wrapped_callback(1)
    test_callback.assert_not_awaited()

    # Five seconds passed.
    await wrapped_callback(3)
    test_callback.assert_awaited_once_with(5)
    test_callback.reset_mock()

    # Six seconds passed.
    await wrapped_callback(3)
    test_callback.assert_not_awaited()

    # Test with non-numeric value.
    with pytest.raises(ValueError):
        await wrapped_callback("banana")
