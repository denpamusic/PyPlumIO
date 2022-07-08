"""Contains tests for callback filters."""

from unittest.mock import AsyncMock

import pytest

from pyplumio.helpers.filters import debounce, on_change


async def test_on_change() -> None:
    """Test on change filter."""
    test_callback = AsyncMock()
    wrapped_callback = on_change(test_callback)
    await wrapped_callback(5)
    test_callback.assert_awaited_once_with(5)
    test_callback.reset_mock()

    # Check that callback is not awaited on insignificant change.
    await wrapped_callback(5.04)
    test_callback.assert_not_awaited()

    await wrapped_callback(5.1)
    test_callback.assert_awaited_once_with(5.1)

    # Test equality with callback function and different instance.
    assert test_callback == wrapped_callback
    assert wrapped_callback == on_change(test_callback)
    with pytest.raises(TypeError):
        _ = wrapped_callback == "you shall not pass"


async def test_debounce() -> None:
    """Test debounce filter."""
    test_callback = AsyncMock()
    wrapped_callback = debounce(test_callback, min_calls=3)
    await wrapped_callback(5)
    test_callback.assert_awaited_once_with(5)
    test_callback.reset_mock()

    # Ignore stray "5" and only await callback with "4".
    await wrapped_callback(4)
    await wrapped_callback(5)
    await wrapped_callback(4)
    await wrapped_callback(4)
    await wrapped_callback(4)
    test_callback.assert_awaited_once_with(4)

    # Test equality with callback function and different instance.
    assert test_callback == wrapped_callback
    assert wrapped_callback == debounce(test_callback)
    with pytest.raises(TypeError):
        _ = wrapped_callback == "you shall not pass"
