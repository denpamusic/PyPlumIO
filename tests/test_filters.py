"""Contains tests for the filter classes."""

from datetime import datetime, timedelta
from importlib import reload
import logging
import sys
from unittest.mock import AsyncMock, patch

import pytest

import pyplumio
from pyplumio import filters
import pyplumio.filters
from pyplumio.parameters import Parameter, ParameterValues
from pyplumio.structures.alerts import Alert


@pytest.fixture(name="use_numpy", params=(True, False))
def fixture_use_numpy(request, monkeypatch, caplog):
    """Try with and without numpy package."""
    if not request.param:
        monkeypatch.setitem(sys.modules, "numpy", None)

    with caplog.at_level(logging.INFO):
        reload(pyplumio.filters)

    message = "Using numpy for improved float precision"
    if request.param:
        assert message in caplog.text
    else:
        assert message not in caplog.text

    return request.param


@pytest.mark.parametrize(
    ("input_value", "expected"),
    [
        (1, 10),
        (50, 15),
        (11, 11),
    ],
)
async def test_clamp(input_value, expected) -> None:
    """Test the clamp filter."""
    test_callback = AsyncMock()
    wrapped_callback = filters.clamp(test_callback, min_value=10, max_value=15)
    await wrapped_callback(input_value)
    test_callback.assert_awaited_once_with(expected)


async def test_deadband() -> None:
    """Test the deadband filter."""
    test_callback = AsyncMock()
    wrapped_callback = filters.deadband(test_callback, tolerance=0.1)
    await wrapped_callback(1)
    test_callback.assert_awaited_once_with(1)
    test_callback.reset_mock()

    # Check that callback is not awaited on insignificant change.
    await wrapped_callback(1.01)
    test_callback.assert_not_awaited()

    await wrapped_callback(1.1)
    test_callback.assert_awaited_once_with(1.1)

    # Test with non-numeric value.
    with pytest.raises(TypeError, match="filter can only be used with numeric values"):
        await wrapped_callback("banana")


async def test_on_change() -> None:
    """Test the value changed filter."""
    test_callback = AsyncMock()
    wrapped_callback = filters.on_change(test_callback)
    await wrapped_callback(1)
    test_callback.assert_awaited_once_with(1)
    test_callback.reset_mock()

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


async def test_throttle(frozen_time) -> None:
    """Test the throttle filter."""
    test_callback = AsyncMock()
    wrapped_callback = filters.throttle(test_callback, seconds=5)
    await wrapped_callback(1)
    test_callback.assert_awaited_once_with(1)
    test_callback.reset_mock()

    # One second passed.
    frozen_time.tick(timedelta(seconds=1))
    await wrapped_callback(2)
    test_callback.assert_not_awaited()

    # Five seconds passed.
    frozen_time.tick(timedelta(seconds=4))
    await wrapped_callback(3)
    test_callback.assert_awaited_once_with(3)
    test_callback.reset_mock()

    # Six seconds passed.
    frozen_time.tick(timedelta(seconds=1))
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


async def test_aggregate(use_numpy, frozen_time) -> None:
    """Test the aggregate filter."""
    test_callback = AsyncMock()
    wrapped_callback = filters.aggregate(test_callback, seconds=5, sample_size=5)
    await wrapped_callback(1)
    test_callback.assert_not_awaited()

    # One second passed.
    frozen_time.tick(timedelta(seconds=1))
    await wrapped_callback(1)
    test_callback.assert_not_awaited()

    # Five seconds passed.
    frozen_time.tick(timedelta(seconds=4))
    if use_numpy:
        with patch("numpy.sum", return_value=5) as mock_sum:
            await wrapped_callback(3)

        mock_sum.assert_called_once_with([1, 1, 3])
    else:
        await wrapped_callback(3)

    test_callback.assert_awaited_once_with(5)
    test_callback.reset_mock()

    # Six second passed.
    frozen_time.tick(timedelta(seconds=1))
    await wrapped_callback(3)
    test_callback.assert_not_awaited()

    # Test with non-numeric value.
    with pytest.raises(TypeError, match="filter can only be used with numeric values"):
        await wrapped_callback("banana")


async def test_aggregate_sample_size(frozen_time) -> None:
    """Test the aggregate filter with sample size."""
    test_callback = AsyncMock()
    wrapped_callback = filters.aggregate(test_callback, seconds=5, sample_size=2)

    # Zero seconds passed, current sample size is 1.
    await wrapped_callback(1)
    test_callback.assert_not_awaited()

    # One second passed, current sample size is 2.
    frozen_time.tick(timedelta(seconds=1))
    await wrapped_callback(1)
    test_callback.assert_awaited_once_with(2)

    # Two seconds passed, current sample size is 3.
    frozen_time.tick(timedelta(seconds=1))
    await wrapped_callback(3)
    test_callback.test_callback.assert_not_awaited()


@pytest.mark.parametrize(
    ("filter_func", "input_value", "callback"),
    [
        (lambda x: len(x) == 4, [1, 2], False),
        (lambda x: len(x) == 4, [1, 2, 3, 4], True),
        (lambda x: len(x) == 4, [], False),
    ],
)
async def test_custom(filter_func, input_value, callback) -> None:
    """Test the custom filter."""
    test_callback = AsyncMock()
    wrapped_callback = filters.custom(test_callback, filter_func)
    await wrapped_callback(input_value)

    if callback:
        test_callback.assert_awaited_once_with(input_value)
    else:
        test_callback.assert_not_awaited()
