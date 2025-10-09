"""Contains tests for the filter classes."""

from datetime import datetime, timedelta
from importlib import reload
import logging
import sys
from typing import Literal
from unittest.mock import AsyncMock, Mock, patch

import pytest

import pyplumio
from pyplumio import filters
from pyplumio.devices.ecomax import EcoMAX
import pyplumio.filters
from pyplumio.helpers.event_manager import Event, EventContext
from pyplumio.parameters import Parameter, ParameterValues
from pyplumio.structures.alerts import Alert
from tests.conftest import RAISES


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


@pytest.fixture(name="event")
def fixture_event(ecomax: EcoMAX) -> Event:
    """Return a test event."""
    return Event("test", originator=ecomax, context=EventContext(value=0))


@pytest.mark.parametrize(
    ("input_value", "expected"),
    [
        (1, 10),
        (50, 15),
        (11, 11),
        ("banana", RAISES),
    ],
)
async def test_clamp(
    input_value: int, expected: int | Literal["raises"], event: Event
) -> None:
    """Test the clamp filter."""
    test_callback = AsyncMock()
    wrapped_callback = filters.clamp(test_callback, min_value=10, max_value=15)
    assert hash(wrapped_callback) == hash(test_callback)

    if expected != RAISES:
        await wrapped_callback(input_value, event)
        test_callback.assert_awaited_once_with(expected, event)
    else:
        # Test with non-numeric value.
        with pytest.raises(
            TypeError, match="filter can only be used with numeric values"
        ):
            await wrapped_callback(input_value, event)


async def test_clamp_ignore_out_of_range(event: Event) -> None:
    """Test the clamp filter with ignore_out_of_range."""
    test_callback = AsyncMock()
    wrapped_callback = filters.clamp(
        test_callback, min_value=10, max_value=15, ignore_out_of_range=True
    )
    await wrapped_callback(1, event)
    test_callback.assert_not_awaited()

    await wrapped_callback(50, event)
    test_callback.assert_not_awaited()

    await wrapped_callback(11, event)
    test_callback.assert_awaited_once_with(11, event)


async def test_deadband(event: Event) -> None:
    """Test the deadband filter."""
    test_callback = AsyncMock()
    wrapped_callback = filters.deadband(test_callback, tolerance=0.1)
    assert hash(wrapped_callback) == hash(test_callback)
    input_value = 1.0
    await wrapped_callback(input_value, event)
    assert wrapped_callback.value == input_value
    test_callback.assert_awaited_once_with(input_value, event)
    test_callback.reset_mock()

    # Check that callback is not awaite and it's value is not changed
    # on insignificant input change.
    await wrapped_callback(1.01, event)
    assert wrapped_callback.value == input_value
    test_callback.assert_not_awaited()

    input_value = 1.1
    await wrapped_callback(input_value, event)
    assert wrapped_callback.value == input_value
    test_callback.assert_awaited_once_with(input_value, event)

    # Test with non-numeric value.
    with pytest.raises(TypeError, match="filter can only be used with numeric values"):
        await wrapped_callback("banana", event)


async def test_on_change(event: Event) -> None:
    """Test the value changed filter."""
    test_callback = AsyncMock()
    wrapped_callback = filters.on_change(test_callback)
    assert hash(wrapped_callback) == hash(test_callback)
    input_value = 1.0
    await wrapped_callback(input_value, event)
    assert wrapped_callback.value == input_value
    test_callback.assert_awaited_once_with(input_value, event)
    test_callback.reset_mock()

    input_value = 1.1
    await wrapped_callback(input_value, event)
    assert wrapped_callback.value == input_value
    test_callback.assert_awaited_once_with(input_value, event)

    # Test equality with callback function and different instance.
    assert test_callback == wrapped_callback
    assert wrapped_callback == filters.on_change(test_callback)
    assert wrapped_callback.__eq__("you shall not pass") is NotImplemented


async def test_on_change_parameter(event: Event) -> None:
    """Test the value changed filter with parameters."""
    test_callback = AsyncMock()
    test_parameter = AsyncMock(spec=Parameter)
    test_parameter.values = ParameterValues(0, 0, 1)
    test_parameter.update_pending.is_set = Mock(return_value=False)
    wrapped_callback = filters.on_change(test_callback)
    assert hash(wrapped_callback) == hash(test_callback)
    await wrapped_callback(test_parameter, event)
    test_callback.assert_awaited_once_with(test_parameter, event)
    test_callback.reset_mock()

    # Check that we're storing a copy instead of an actual parameter.
    assert wrapped_callback.value == test_parameter
    assert wrapped_callback.value is not test_parameter

    # Check that callback is not awaited with no change.
    await wrapped_callback(test_parameter, event)
    test_callback.assert_not_awaited()

    # Check that callback is awaited on local value change.
    test_parameter.update_pending.is_set.return_value = True
    await wrapped_callback(test_parameter, event)
    test_callback.assert_awaited_once_with(test_parameter, event)
    test_callback.reset_mock()
    test_parameter.update_pending.is_set.return_value = False

    # Check that callback is awaited on remote value change.
    test_parameter.values = ParameterValues(1, 0, 1)
    await wrapped_callback(test_parameter, event)
    test_callback.assert_awaited_once_with(test_parameter, event)
    test_callback.reset_mock()

    # Check that callback is awaited on min value change.
    test_parameter.values = ParameterValues(1, 1, 1)
    await wrapped_callback(test_parameter, event)
    test_callback.assert_awaited_once_with(test_parameter, event)
    test_callback.reset_mock()

    # Check that callback is awaited on max value change.
    test_parameter.values = ParameterValues(1, 1, 2)
    await wrapped_callback(test_parameter, event)
    test_callback.assert_awaited_once_with(test_parameter, event)


async def test_debounce(event: Event) -> None:
    """Test the debounce filter."""
    test_callback = AsyncMock()
    wrapped_callback = filters.debounce(test_callback, min_calls=3)
    assert hash(wrapped_callback) == hash(test_callback)

    input_value = 1
    await wrapped_callback(input_value, event)
    assert wrapped_callback.value == input_value
    test_callback.assert_awaited_once_with(input_value, event)
    test_callback.reset_mock()

    # Ignore stray "1" and only await callback on a "2".
    input_value2 = 2
    await wrapped_callback(input_value2, event)
    assert wrapped_callback.value == input_value
    await wrapped_callback(input_value, event)
    assert wrapped_callback.value == input_value
    await wrapped_callback(input_value2, event)
    assert wrapped_callback.value == input_value
    await wrapped_callback(input_value2, event)
    assert wrapped_callback.value == input_value
    await wrapped_callback(input_value2, event)
    assert wrapped_callback.value == input_value2
    test_callback.assert_awaited_once_with(input_value2, event)


async def test_throttle(frozen_time, event: Event) -> None:
    """Test the throttle filter."""
    test_callback = AsyncMock()
    wrapped_callback = filters.throttle(test_callback, seconds=5)
    assert hash(wrapped_callback) == hash(test_callback)
    await wrapped_callback(1, event)
    test_callback.assert_awaited_once_with(1, event)
    test_callback.reset_mock()

    # One second passed.
    frozen_time.tick(timedelta(seconds=1))
    await wrapped_callback(2, event)
    test_callback.assert_not_awaited()

    # Five seconds passed.
    frozen_time.tick(timedelta(seconds=4))
    await wrapped_callback(3, event)
    test_callback.assert_awaited_once_with(3, event)
    test_callback.reset_mock()

    # Six seconds passed.
    frozen_time.tick(timedelta(seconds=1))
    await wrapped_callback(4, event)
    test_callback.assert_not_awaited()


async def test_delta(event: Event) -> None:
    """Test the delta filter."""
    test_callback = AsyncMock()
    wrapped_callback = filters.delta(test_callback)
    assert hash(wrapped_callback) == hash(test_callback)

    await wrapped_callback(5, event)
    test_callback.assert_not_awaited()

    await wrapped_callback(3, event)
    test_callback.assert_awaited_once_with(-2, event)
    test_callback.reset_mock()

    # Test with list of alerts.
    alert1 = Alert(code=0, from_dt=datetime.now(), to_dt=None)
    alert2 = Alert(code=1, from_dt=datetime.now(), to_dt=None)
    alert3 = Alert(code=2, from_dt=datetime.now(), to_dt=None)
    wrapped_callback = filters.delta(test_callback)
    await wrapped_callback([alert1, alert2], event)
    await wrapped_callback([alert3, alert2], event)
    test_callback.assert_awaited_once_with([alert3], event)
    test_callback.reset_mock()

    # Test with unknown.
    wrapped_callback = filters.delta(test_callback)
    await wrapped_callback("foo", event)
    await wrapped_callback("bar", event)
    test_callback.assert_not_awaited()


async def test_aggregate(use_numpy, frozen_time, event: Event) -> None:
    """Test the aggregate filter."""
    test_callback = AsyncMock()
    wrapped_callback = filters.aggregate(test_callback, seconds=5, sample_size=5)
    assert hash(wrapped_callback) == hash(test_callback)
    await wrapped_callback(1, event)
    test_callback.assert_not_awaited()

    # One second passed.
    frozen_time.tick(timedelta(seconds=1))
    await wrapped_callback(1, event)
    test_callback.assert_not_awaited()

    # Five seconds passed.
    frozen_time.tick(timedelta(seconds=4))
    if use_numpy:
        with (
            patch("numpy.sum", return_value=5) as mock_sum,
            patch("numpy.array") as mock_array,
        ):
            await wrapped_callback(3, event)

        mock_array.assert_called_once_with([1, 1, 3])
        mock_sum.assert_called_once_with(mock_array.return_value)
    else:
        await wrapped_callback(3, event)

    test_callback.assert_awaited_once_with(5, event)
    test_callback.reset_mock()

    # Six second passed.
    frozen_time.tick(timedelta(seconds=1))
    await wrapped_callback(3, event)
    test_callback.assert_not_awaited()

    # Test with non-numeric value.
    with pytest.raises(TypeError, match="filter can only be used with numeric values"):
        await wrapped_callback("banana", event)


async def test_aggregate_sample_size(frozen_time, event: Event) -> None:
    """Test the aggregate filter with sample size."""
    test_callback = AsyncMock()
    wrapped_callback = filters.aggregate(test_callback, seconds=5, sample_size=2)
    assert hash(wrapped_callback) == hash(test_callback)

    # Zero seconds passed, current sample size is 1.
    await wrapped_callback(1, event)
    test_callback.assert_not_awaited()

    # One second passed, current sample size is 2.
    frozen_time.tick(timedelta(seconds=1))
    await wrapped_callback(1, event)
    test_callback.assert_awaited_once_with(2, event)

    # Two seconds passed, current sample size is 3.
    frozen_time.tick(timedelta(seconds=1))
    await wrapped_callback(3, event)
    test_callback.test_callback.assert_not_awaited()


@pytest.mark.parametrize(
    ("filter_func", "input_value", "callback"),
    [
        (lambda x: len(x) == 4, [1, 2], False),
        (lambda x: len(x) == 4, [1, 2, 3, 4], True),
        (lambda x: len(x) == 4, [], False),
    ],
)
async def test_custom(filter_func, input_value, callback, event: Event) -> None:
    """Test the custom filter."""
    test_callback = AsyncMock()
    wrapped_callback = filters.custom(test_callback, filter_func)
    assert hash(wrapped_callback) == hash(test_callback)
    await wrapped_callback(input_value, event)

    if callback:
        test_callback.assert_awaited_once_with(input_value, event)
    else:
        test_callback.assert_not_awaited()
