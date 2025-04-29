"""Contains tests for the filter classes."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from pyplumio import filters
from pyplumio.parameters import Parameter, ParameterValues
from pyplumio.structures.alerts import Alert


async def test_clamp() -> None:
    """Test the clamp filter."""
    test_callback = AsyncMock()
    wrapped_callback = filters.clamp(test_callback, min_value=10, max_value=15)
    await wrapped_callback(1)
    test_callback.assert_awaited_once_with(10)
    test_callback.reset_mock()

    await wrapped_callback(50)
    test_callback.assert_awaited_once_with(15)
    test_callback.reset_mock()

    await wrapped_callback(11)
    test_callback.assert_awaited_once_with(11)


async def test_on_change() -> None:
    """Test the value changed filter."""
    test_callback = AsyncMock()
    wrapped_callback = filters.on_change(test_callback)
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
    assert wrapped_callback == filters.on_change(test_callback)
    assert wrapped_callback.__eq__("you shall not pass") is NotImplemented


async def test_on_change_parameter() -> None:
    """Test the value changed filter with parameters."""
    test_callback = AsyncMock()
    test_parameter = AsyncMock(spec=Parameter)
    test_parameter.values = ParameterValues(0, 0, 1)
    test_parameter.pending_update = False
    wrapped_callback = filters.on_change(test_callback)
    await wrapped_callback(test_parameter)
    test_callback.assert_awaited_once_with(test_parameter)
    test_callback.reset_mock()

    # Check that callback is not awaited with no change.
    await wrapped_callback(test_parameter)
    test_callback.assert_not_awaited()

    # Check that callback is awaited on local value change.
    test_parameter.pending_update = True
    await wrapped_callback(test_parameter)
    test_callback.assert_awaited_once_with(test_parameter)
    test_callback.reset_mock()
    test_parameter.pending_update = False

    # Check that callback is awaited on remote value change.
    test_parameter.values = ParameterValues(1, 0, 1)
    await wrapped_callback(test_parameter)
    test_callback.assert_awaited_once_with(test_parameter)
    test_callback.reset_mock()

    # Check that callback is awaited on min value change.
    test_parameter.values = ParameterValues(1, 1, 1)
    await wrapped_callback(test_parameter)
    test_callback.assert_awaited_once_with(test_parameter)
    test_callback.reset_mock()

    # Check that callback is awaited on max value change.
    test_parameter.values = ParameterValues(1, 1, 2)
    await wrapped_callback(test_parameter)
    test_callback.assert_awaited_once_with(test_parameter)


async def test_debounce() -> None:
    """Test the debounce filter."""
    test_callback = AsyncMock()
    wrapped_callback = filters.debounce(test_callback, min_calls=3)
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


@patch("time.monotonic", side_effect=(0, 1, 5, 6))
async def test_throttle(mock_time) -> None:
    """Test the throttle filter."""
    test_callback = AsyncMock()
    wrapped_callback = filters.throttle(test_callback, seconds=5)
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
    """Test the delta filter."""
    test_callback = AsyncMock()
    wrapped_callback = filters.delta(test_callback)

    await wrapped_callback(5)
    test_callback.assert_not_awaited()

    await wrapped_callback(3)
    test_callback.assert_awaited_once_with(-2)
    test_callback.reset_mock()

    # Test with list of alerts.
    alert1 = Alert(code=0, from_dt=datetime.now(), to_dt=None)
    alert2 = Alert(code=1, from_dt=datetime.now(), to_dt=None)
    alert3 = Alert(code=2, from_dt=datetime.now(), to_dt=None)
    wrapped_callback = filters.delta(test_callback)
    await wrapped_callback([alert1, alert2])
    await wrapped_callback([alert3, alert2])
    test_callback.assert_awaited_once_with([alert3])
    test_callback.reset_mock()

    # Test with unknown.
    wrapped_callback = filters.delta(test_callback)
    await wrapped_callback("foo")
    await wrapped_callback("bar")
    test_callback.assert_not_awaited()


@patch("time.monotonic", side_effect=(0, 0, 1, 5, 6, 7))
async def test_aggregate(mock_time) -> None:
    """Test the aggregate filter."""
    test_callback = AsyncMock()
    wrapped_callback = filters.aggregate(test_callback, seconds=5, sample_size=5)

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
    with pytest.raises(TypeError):
        await wrapped_callback("banana")


@patch("time.monotonic", side_effect=(0, 0, 1, 1, 1, 1))
async def test_aggregate_sample_size(mock_time) -> None:
    """Test the aggregate filter with sample size."""
    test_callback = AsyncMock()
    wrapped_callback = filters.aggregate(test_callback, seconds=5, sample_size=2)

    # Zero seconds passed, sample size 1.
    await wrapped_callback(1)
    test_callback.assert_not_awaited()

    # One second passed, sample size 2.
    await wrapped_callback(1)
    test_callback.assert_awaited_once_with(2)

    # Two seconds passed, sample size 3.
    await wrapped_callback(3)
    test_callback.test_callback.assert_not_awaited()


async def test_custom() -> None:
    """Test the custom filter."""
    test_callback = AsyncMock()
    wrapped_callback = filters.custom(test_callback, lambda x: len(x) == 4)

    # Test that callback is not called when a list contains 2 items.
    await wrapped_callback([1, 2])
    test_callback.assert_not_awaited()

    # Test that callback is called when a list contains 4 items.
    await wrapped_callback([1, 2, 3, 4])
    test_callback.assert_awaited_once_with([1, 2, 3, 4])
    test_callback.reset_mock()

    # Test that callback is not called when list is empty.
    await wrapped_callback([])
    test_callback.assert_not_awaited()
