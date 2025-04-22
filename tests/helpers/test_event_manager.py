"""Contains tests for the event manager."""

from typing import Any
from unittest.mock import AsyncMock, Mock, call, patch

import pytest

from pyplumio.helpers.event_manager import EventManager, event_listener


@pytest.fixture(name="event_manager")
def fixture_event_manager() -> EventManager:
    """Return an event manager object."""
    event_manager = EventManager[Any]()
    event_manager.data = {"test_key": "test_value"}
    return event_manager


def test_register_event_listeners() -> None:
    """Test registering event listeners."""
    with (
        patch(
            "pyplumio.helpers.event_manager.EventManager.on_event_test", create=True
        ) as mock_on_event_test,
        patch(
            "pyplumio.helpers.event_manager.EventManager.on_event_test2", create=True
        ) as mock_on_event_test2,
        patch(
            "pyplumio.helpers.event_manager.EventManager.subscribe", autospec=True
        ) as mock_subscribe,
    ):
        # Mark mock_listener as event listener.
        setattr(mock_on_event_test, "_on_event", "test")
        setattr(mock_on_event_test, "_on_event_filter", None)

        # Mark mock_listener2 as event listener with a filter.
        mock_filter = Mock()
        mock_wrapper = Mock(return_value=mock_filter)
        setattr(mock_on_event_test2, "_on_event", "test2")
        setattr(mock_on_event_test2, "_on_event_filter", mock_wrapper)

        event_manager = EventManager[Any]()

    mock_subscribe.assert_has_calls(
        [
            call(event_manager, "test", mock_on_event_test),
            call(event_manager, "test2", mock_filter),
        ]
    )

    # Assert that filter function was called with mock_listener2 as
    # it's argument.
    mock_wrapper.assert_called_once_with(mock_on_event_test2)


def test_getattr(event_manager: EventManager) -> None:
    """Test getting an event manager attribute."""
    assert event_manager.test_key == "test_value"


async def test_wait_for(event_manager: EventManager) -> None:
    """Test waiting for event."""
    with (
        patch("asyncio.wait_for") as mock_wait_for,
        patch(
            "pyplumio.helpers.event_manager.EventManager.create_event"
        ) as mock_create_event,
    ):
        mock_create_event.wait = AsyncMock()
        await event_manager.wait_for("test_key2")

    mock_create_event.assert_called_with("test_key2")
    mock_wait_for.assert_awaited_once_with(
        mock_create_event.return_value.wait.return_value, timeout=None
    )


async def test_get(event_manager: EventManager) -> None:
    """Test getting an event value."""
    assert await event_manager.get("test_key") == "test_value"
    assert event_manager.test_key == "test_value"
    with pytest.raises(AttributeError):
        event_manager.nonexistent


def test_get_nowait(event_manager: EventManager) -> None:
    """Test getting an event value without waiting."""
    assert event_manager.get_nowait("test_key") == "test_value"
    assert event_manager.get_nowait("test_key2") is None


async def test_load(event_manager: EventManager) -> None:
    """Test loading event data."""
    callback = AsyncMock(return_value=True)
    callback2 = AsyncMock(return_value=True)
    event_manager.subscribe("test_key1", callback)
    event_manager.subscribe("test_key2", callback2)
    event_manager.load_nowait({"test_key2": "test_value2"})
    await event_manager.wait_until_done()
    callback.assert_not_awaited()
    callback2.assert_awaited_once_with("test_value2")


async def test_load_nowait(event_manager: EventManager) -> None:
    """Test loading event data without waiting."""
    callback = AsyncMock(return_value=True)
    callback2 = AsyncMock(return_value=True)
    event_manager.subscribe("test_key1", callback)
    event_manager.subscribe("test_key2", callback2)
    await event_manager.load({"test_key2": "test_value2"})
    callback.assert_not_awaited()
    callback2.assert_awaited_once_with("test_value2")


async def test_subscribe(event_manager: EventManager) -> None:
    """Test subscribing to an event."""
    callback = AsyncMock(return_value=True)
    assert event_manager.subscribe("test_key2", callback) is callback
    event_manager.dispatch_nowait("test_key2", "test_value2")
    event_manager.dispatch_nowait("test_key2", "test_value3")
    await event_manager.wait_until_done()
    callback.assert_has_awaits([call("test_value2"), call("test_value3")])


async def test_subscribe_once(event_manager: EventManager) -> None:
    """Test subscribing to an event once."""
    callback = AsyncMock(return_value=True)
    event_manager.subscribe_once("test_key2", callback)
    event_manager.dispatch_nowait("test_key2", "test_value2")
    event_manager.dispatch_nowait("test_key2", "test_value3")
    await event_manager.wait_until_done()
    callback.assert_awaited_once_with("test_value2")
    callback.reset_mock()

    # Test getting the reference and unsubscribing.
    with patch(
        "pyplumio.helpers.event_manager.EventManager.unsubscribe"
    ) as mock_unsubscribe:
        callback2 = event_manager.subscribe_once("test_key3", callback)
        event_manager.unsubscribe("test_key3", callback2)
        await event_manager.wait_until_done()

    mock_unsubscribe.assert_called_once_with("test_key3", callback2)
    callback.assert_not_awaited()


async def test_subscribe_once_interrupt(event_manager: EventManager) -> None:
    """Test subscribing once doesn't affect other callbacks."""
    callback1 = AsyncMock(return_value=None)
    callback2 = AsyncMock(return_value=None)
    event_manager.subscribe_once("test_key1", callback1)
    assert event_manager.subscribe("test_key1", callback2) is callback2
    event_manager.dispatch_nowait("test_key1", "test_value1")
    event_manager.dispatch_nowait("test_key1", "test_value2")
    await event_manager.wait_until_done()
    callback2.assert_has_awaits([call("test_value1"), call("test_value2")])


async def test_unsubscribe(event_manager: EventManager) -> None:
    """Test unsubscribing from the event."""
    callback = AsyncMock(return_value=True)
    event_manager.subscribe("test_key2", callback)
    assert event_manager.unsubscribe("test_key2", callback)
    assert not event_manager.unsubscribe("test_key3", callback)
    event_manager.dispatch_nowait("test_key2", "test_value2")
    await event_manager.wait_until_done()
    callback.assert_not_awaited()


def test_create_event(event_manager: EventManager) -> None:
    """Test creating an event."""
    event = event_manager.create_event("test")
    assert event == event_manager.create_event("test")
    assert "test" in event_manager.events
    assert not event_manager.events["test"].is_set()
    event_manager.set_event("test")
    assert event_manager.events["test"].is_set()


def test_event_listener_decorator() -> None:
    """Test subscribe decorator."""
    mock_func = Mock()
    decorator = event_listener("test")
    assert decorator(mock_func)
    assert getattr(mock_func, "_on_event") == "test"
    assert not getattr(mock_func, "_on_event_filter")

    # Test with filter.
    mock_func = Mock()
    mock_filter = Mock()
    decorator = event_listener("test", mock_filter)
    assert decorator(mock_func)
    assert getattr(mock_func, "_on_event") == "test"
    assert getattr(mock_func, "_on_event_filter") == mock_filter
