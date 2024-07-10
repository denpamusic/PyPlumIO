"""Contains tests for the filter classes."""

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from pyplumio.filters import aggregate, custom, debounce, delta, on_change, throttle
from pyplumio.helpers.event_manager import Event
from pyplumio.helpers.parameter import Parameter, ParameterValues
from pyplumio.structures.alerts import Alert

SOURCE = Mock()
FIRED_AT = Mock()


@pytest.fixture()
def event():
    """Create a event for data."""

    def _create_event(data: Any) -> Event:
        """Create an event."""
        return Event(name="test_event", data=data, source=SOURCE, fired_at=FIRED_AT)

    return _create_event


async def test_on_change(event) -> None:
    """Test on change filter."""
    test_callback = AsyncMock()
    wrapped_callback = on_change(test_callback)
    event1 = event(1)
    await wrapped_callback(event1)
    test_callback.assert_awaited_once_with(event1)
    test_callback.reset_mock()

    # Check that callback is not awaited on insignificant change.
    event2 = event(1.01)
    await wrapped_callback(event2)
    test_callback.assert_not_awaited()

    event3 = event(1.1)
    await wrapped_callback(event3)
    test_callback.assert_awaited_once_with(event3)

    # Test equality with callback function and different instance.
    assert test_callback == wrapped_callback
    assert wrapped_callback == on_change(test_callback)
    assert wrapped_callback.__eq__("you shall not pass") is NotImplemented


async def test_on_change_parameter(event) -> None:
    """Test on change filter with parameters."""
    test_callback = AsyncMock()
    test_parameter = AsyncMock(spec=Parameter)
    test_parameter.values = ParameterValues(0, 0, 1)
    test_parameter.pending_update = False
    event1 = event(test_parameter)
    wrapped_callback = on_change(test_callback)
    await wrapped_callback(event1)
    test_callback.assert_awaited_once_with(event1)
    test_callback.reset_mock()

    # Check that callback is not awaited with no change.
    await wrapped_callback(event1)
    test_callback.assert_not_awaited()

    # Check that callback is awaited on local value change.
    event1.data.pending_update = True
    await wrapped_callback(event1)
    test_callback.assert_awaited_once_with(event1)
    test_callback.reset_mock()
    event1.data.pending_update = False

    # Check that callback is awaited on remote value change.
    event1.data.values = ParameterValues(1, 0, 1)
    await wrapped_callback(event1)
    test_callback.assert_awaited_once_with(event1)
    test_callback.reset_mock()

    # Check that callback is awaited on min value change.
    event1.data.values = ParameterValues(1, 1, 1)
    await wrapped_callback(event1)
    test_callback.assert_awaited_once_with(event1)
    test_callback.reset_mock()

    # Check that callback is awaited on max value change.
    event1.data.values = ParameterValues(1, 1, 2)
    await wrapped_callback(event1)
    test_callback.assert_awaited_once_with(event1)


async def test_debounce(event) -> None:
    """Test debounce filter."""
    test_callback = AsyncMock()
    wrapped_callback = debounce(test_callback, min_calls=3)
    event1 = event(1)
    await wrapped_callback(event1)
    test_callback.assert_awaited_once_with(event1)
    test_callback.reset_mock()

    # Ignore stray "1" and only await callback on a "2".
    event2 = event(2)
    await wrapped_callback(event2)
    await wrapped_callback(event1)
    await wrapped_callback(event2)
    await wrapped_callback(event2)
    await wrapped_callback(event2)
    test_callback.assert_awaited_once_with(event2)


@patch("time.monotonic", side_effect=(0, 1, 5, 6))
async def test_throttle(mock_time, event) -> None:
    """Test throttle filter."""
    test_callback = AsyncMock()
    wrapped_callback = throttle(test_callback, seconds=5)
    event1 = event(1)
    await wrapped_callback(event1)
    test_callback.assert_awaited_once_with(event1)
    test_callback.reset_mock()

    # One second passed.
    event2 = event(2)
    await wrapped_callback(event2)
    test_callback.assert_not_awaited()

    # Five seconds passed.
    event3 = event(3)
    await wrapped_callback(event3)
    test_callback.assert_awaited_once_with(event3)
    test_callback.reset_mock()

    # Six seconds passed.
    event4 = event(4)
    await wrapped_callback(event4)
    test_callback.assert_not_awaited()


async def test_delta(event) -> None:
    """Test delta filter."""
    test_callback = AsyncMock()
    wrapped_callback = delta(test_callback)
    await wrapped_callback(event(5))
    test_callback.assert_not_awaited()

    await wrapped_callback(event(3))
    test_callback.assert_awaited_once_with(event(-2))
    test_callback.reset_mock()

    # Test with list of alerts.
    alert1 = Alert(code=0, from_dt=datetime.now(), to_dt=None)
    alert2 = Alert(code=1, from_dt=datetime.now(), to_dt=None)
    alert3 = Alert(code=2, from_dt=datetime.now(), to_dt=None)
    wrapped_callback = delta(test_callback)
    await wrapped_callback(event([alert1, alert2]))
    await wrapped_callback(event([alert3, alert2]))
    test_callback.assert_awaited_once_with(event([alert3]))
    test_callback.reset_mock()

    # Test with unknown.
    wrapped_callback = delta(test_callback)
    await wrapped_callback(event("foo"))
    await wrapped_callback(event("bar"))
    test_callback.assert_not_awaited()


@patch("time.monotonic", side_effect=(0, 0, 1, 5, 6, 7))
async def test_aggregate(mock_time, event) -> None:
    """Test aggregate filter."""
    test_callback = AsyncMock()
    wrapped_callback = aggregate(test_callback, seconds=5)

    # Zero seconds passed.
    await wrapped_callback(event(1))
    test_callback.assert_not_awaited()

    # One second passed.
    await wrapped_callback(event(1))
    test_callback.assert_not_awaited()

    # Five seconds passed.
    await wrapped_callback(event(3))
    test_callback.assert_awaited_once_with(event(5))
    test_callback.reset_mock()

    # Six seconds passed.
    await wrapped_callback(event(3))
    test_callback.assert_not_awaited()

    # Test with non-numeric value.
    with pytest.raises(ValueError):
        await wrapped_callback(event("banana"))


async def test_custom(event) -> None:
    """Test custom filter."""
    test_callback = AsyncMock()
    wrapped_callback = custom(test_callback, lambda x: len(x) == 4)

    # Test that callback is not called when a list contains 2 items.
    await wrapped_callback(event([1, 2]))
    test_callback.assert_not_awaited()

    # Test that callback is called when a list contains 4 items.
    await wrapped_callback(event([1, 2, 3, 4]))
    test_callback.assert_awaited_once_with(event([1, 2, 3, 4]))
    test_callback.reset_mock()

    # Test that callback is not called when list is empty.
    await wrapped_callback(event([]))
    test_callback.assert_not_awaited()
