"""Contains tests for the event manager."""

from unittest.mock import AsyncMock, call, patch

import pytest

from pyplumio.helpers.event_manager import EventManager


@pytest.fixture(name="event_manager")
def fixture_event_manager() -> EventManager:
    """Return an event manager object."""
    event_manager = EventManager()
    event_manager.data = {"test_key": "test_value"}
    return event_manager


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
    with (
        patch("pyplumio.helpers.event_manager.Event") as mock_event,
        patch("datetime.datetime") as mock_dt,
    ):
        mock_dt.now.return_value = "test"
        await event_manager.wait_until_done()

    callback.assert_not_awaited()
    callback2.assert_awaited_once_with(mock_event.return_value)
    mock_event.assert_called_once_with(
        "test_key2", data="test_value2", source=event_manager, fired_at="test"
    )


async def test_load_nowait(event_manager: EventManager) -> None:
    """Test loading event data without waiting."""
    callback = AsyncMock(return_value=True)
    callback2 = AsyncMock(return_value=True)
    event_manager.subscribe("test_key1", callback)
    event_manager.subscribe("test_key2", callback2)
    with (
        patch("pyplumio.helpers.event_manager.Event") as mock_event,
        patch("datetime.datetime") as mock_dt,
    ):
        mock_dt.now.return_value = "test"
        await event_manager.load({"test_key2": "test_value2"})

    callback.assert_not_awaited()
    callback2.assert_awaited_once()
    mock_event.assert_called_once_with(
        "test_key2", data="test_value2", source=event_manager, fired_at="test"
    )


async def test_subscribe(event_manager: EventManager) -> None:
    """Test subscribing to an event."""
    callback = AsyncMock(return_value=True)
    event_manager.subscribe("test_key2", callback)
    event_manager.dispatch_nowait("test_key2", "test_value2")
    event_manager.dispatch_nowait("test_key2", "test_value3")
    with (
        patch("pyplumio.helpers.event_manager.Event") as mock_event,
        patch("datetime.datetime") as mock_dt,
    ):
        mock_dt.now.return_value = "test"
        await event_manager.wait_until_done()

    assert callback.await_count == 2
    events = [
        call("test_key2", data="test_value2", source=event_manager, fired_at="test"),
        call("test_key2", data="test_value3", source=event_manager, fired_at="test"),
    ]
    mock_event.assert_has_calls(events)


async def test_subscribe_once(event_manager: EventManager) -> None:
    """Test subscribing to an event once."""
    callback = AsyncMock(return_value=True)
    event_manager.subscribe_once("test_key2", callback)
    event_manager.dispatch_nowait("test_key2", "test_value2")
    event_manager.dispatch_nowait("test_key2", "test_value3")
    with (
        patch("pyplumio.helpers.event_manager.Event") as mock_event,
        patch("datetime.datetime") as mock_dt,
    ):
        mock_dt.now.return_value = "test"
        await event_manager.wait_until_done()

    callback.assert_awaited_once()
    mock_event.assert_called_once_with(
        "test_key2", data="test_value2", source=event_manager, fired_at="test"
    )


async def test_unsubscribe(event_manager: EventManager) -> None:
    """Test unsubscribing from the event."""
    callback = AsyncMock(return_value=True)
    event_manager.subscribe("test_key2", callback)
    event_manager.unsubscribe("test_key2", callback)
    event_manager.dispatch_nowait("test_key2", "test_value2")
    await event_manager.wait_until_done()
    callback.assert_not_awaited()


async def test_create_event(event_manager: EventManager) -> None:
    """Test creating an event."""
    event = event_manager.create_event("test")
    assert event == event_manager.create_event("test")
    assert "test" in event_manager.events
    assert not event_manager.events["test"].is_set()
    event_manager.set_event("test")
    assert event_manager.events["test"].is_set()
