"""Contains tests for the event manager."""

from typing import Any
from unittest.mock import AsyncMock, Mock, call, patch

import pytest

from pyplumio.filters import Filter, on_change, throttle
from pyplumio.helpers.event_manager import EventManager, StopPropagation, event_listener


@pytest.fixture(name="event_manager")
async def fixture_event_manager() -> EventManager:
    """Return an event manager object."""
    event_manager = EventManager[Any]()
    await event_manager.dispatch("test_key", "test_value")
    return event_manager


def test_register_event_listeners() -> None:
    """Test registering event listeners."""
    # Create event listener.
    mock_on_event_test = AsyncMock()
    setattr(mock_on_event_test, "_on_event", "test")
    setattr(mock_on_event_test, "_on_event_filter", None)

    # Create event listener with filter.
    mock_on_event_test2 = AsyncMock()
    setattr(mock_on_event_test2, "_on_event", "test2")
    mock_filter = Mock(spec=Filter)
    mock_wrapper = Mock(return_value=mock_filter)
    setattr(mock_on_event_test2, "_on_event_filter", mock_wrapper)

    mock_event_listeners = [
        ("on_event_test", mock_on_event_test),
        ("on_event_test2", mock_on_event_test2),
    ]

    with patch("inspect.getmembers", return_value=mock_event_listeners):
        event_manager = EventManager[Any]()
        assert list(event_manager.event_listeners()) == [
            ("test", mock_on_event_test),
            ("test2", mock_on_event_test2),
        ]

    assert event_manager._listeners == {
        "test": [mock_on_event_test],
        "test2": [mock_filter],
    }
    assert event_manager._callbacks == {}

    # Assert that filter function was called with mock_listener2 as
    # its argument.
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
    event_manager.subscribe("test_key2", callback)
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

    # Test unsubscribing before the event is dispatched.
    unsubscribe_callback = event_manager.subscribe_once("test_key3", callback)
    unsubscribe_callback()
    await event_manager.dispatch("test_key3", "test_value4")
    callback.assert_not_awaited()
    unsubscribe_callback()


async def test_subscribe_once_interrupt(event_manager: EventManager) -> None:
    """Test subscribing once doesn't affect other callbacks."""
    callback1 = AsyncMock(return_value=None)
    callback2 = AsyncMock(return_value=None)
    event_manager.subscribe_once("test_key1", callback1)
    event_manager.subscribe("test_key1", callback2)
    event_manager.dispatch_nowait("test_key1", "test_value1")
    event_manager.dispatch_nowait("test_key1", "test_value2")
    await event_manager.wait_until_done()
    callback2.assert_has_awaits([call("test_value1"), call("test_value2")])


async def test_unsubscribe(event_manager: EventManager) -> None:
    """Test unsubscribing from the event."""
    callback = AsyncMock(return_value=True)
    unsubscribe = event_manager.subscribe("test_key2", callback)
    await event_manager.dispatch("test_key2", "test_value1")
    callback.assert_awaited_once_with("test_value1")
    callback.reset_mock()
    unsubscribe()
    await event_manager.dispatch("test_key2", "test_value2")
    callback.assert_not_awaited()
    unsubscribe()


async def test_unsubscribe_same_callback_with_filters(
    event_manager: EventManager,
) -> None:
    """Test unsubscribing filtered wrappers of the same callback independently."""
    callback = AsyncMock(return_value=None)
    unsub_plain = event_manager.subscribe("test_key2", callback)
    unsub_on_change = event_manager.subscribe("test_key2", on_change(callback))
    unsub_throttled = event_manager.subscribe("test_key2", throttle(callback, 5))

    unsub_on_change()
    await event_manager.dispatch("test_key2", "test_value1")
    assert callback.await_count == 2
    callback.assert_has_awaits([call("test_value1"), call("test_value1")])

    callback.reset_mock()
    unsub_throttled()
    unsub_throttled()
    await event_manager.dispatch("test_key2", "test_value2")
    callback.assert_awaited_once_with("test_value2")

    callback.reset_mock()
    unsub_plain()
    await event_manager.dispatch("test_key2", "test_value3")
    callback.assert_not_awaited()


async def test_dispatch_with_callback_error(
    event_manager: EventManager, caplog
) -> None:
    """Test dispatching an event with callback error."""
    callback = AsyncMock(side_effect=(OSError,))
    event_manager.subscribe("test_key1", callback)
    await event_manager.dispatch("test_key1", "test_value1")
    assert "Error in event listener" in caplog.text


async def test_dispatch_with_stop_propagation(event_manager: EventManager) -> None:
    """Test dispatching an event to callback that stops propagation."""
    callback1 = AsyncMock(return_value=StopPropagation)
    callback2 = AsyncMock()
    event_manager.subscribe("test_key1", callback1)
    event_manager.subscribe("test_key1", callback2)
    await event_manager.dispatch("test_key1", "test_value1")
    callback1.assert_awaited_once_with("test_value1")
    callback2.assert_not_awaited()


async def test_dispatch_three_stage_order_and_visibility() -> None:
    """Test that internal listeners commit state before external callbacks run."""
    call_order: list[str] = []
    seen_in_listener: dict[str, Any] = {}
    seen_in_external: list[tuple[bool, Any, Any, bool]] = []

    class _Manager(EventManager[Any]):
        """Represent a test event manager with an internal listener."""

        __slots__ = ()

        @event_listener
        async def on_event_custom(self, value: str) -> str:
            """Transform the custom event value."""
            call_order.append("listener")
            seen_in_listener["in_data"] = "custom" in self.data
            seen_in_listener["event_set"] = self.events["custom"].is_set()
            return f"{value}_transformed"

    manager = _Manager()
    event = manager.create_event("custom")

    async def on_subscribe(value: str) -> None:
        """Observe state in a regular subscriber."""
        call_order.append("subscribe")
        seen_in_external.append(
            (
                "custom" in manager.data,
                manager.data["custom"],
                manager.get_nowait("custom"),
                event.is_set(),
            )
        )
        assert value == "raw_transformed"

    async def on_subscribe_once(value: str) -> None:
        """Observe state in a one-shot subscriber."""
        call_order.append("subscribe_once")
        seen_in_external.append(
            (
                "custom" in manager.data,
                manager.data["custom"],
                manager.get_nowait("custom"),
                event.is_set(),
            )
        )
        assert value == "raw_transformed"

    manager.subscribe("custom", on_subscribe)
    manager.subscribe_once("custom", on_subscribe_once)
    await manager.dispatch("custom", "raw")

    assert call_order == ["listener", "subscribe", "subscribe_once"]
    assert seen_in_listener == {"in_data": False, "event_set": False}
    assert seen_in_external == [
        (True, "raw_transformed", "raw_transformed", True),
        (True, "raw_transformed", "raw_transformed", True),
    ]
    assert manager.data["custom"] == "raw_transformed"
    assert event.is_set()


async def test_dispatch_external_callback_replacement_visibility(
    event_manager: EventManager,
) -> None:
    """Test that external callback replacements update data immediately."""
    observed: list[tuple[str, str, Any]] = []

    async def callback1(value: str) -> str:
        """Return a replacement value."""
        assert value == "initial"
        assert event_manager.data["test_key2"] == "initial"
        return "replaced"

    async def callback2(value: str) -> None:
        """Record the value and immediate data state."""
        observed.append(
            (
                value,
                event_manager.data["test_key2"],
                event_manager.get_nowait("test_key2"),
            )
        )

    event_manager.subscribe("test_key2", callback1)
    event_manager.subscribe("test_key2", callback2)
    await event_manager.dispatch("test_key2", "initial")

    assert observed == [("replaced", "replaced", "replaced")]
    assert event_manager.data["test_key2"] == "replaced"


async def test_dispatch_stop_propagation_in_event_listener() -> None:
    """Test that StopPropagation in an internal listener commits and stops."""
    third_listener_called = False

    class _Manager(EventManager[Any]):
        """Represent a test event manager with multiple internal listeners."""

        __slots__ = ()

        @event_listener("custom")
        async def on_event_a(self, value: str) -> str:
            """Transform the value before stopping propagation."""
            return f"{value}_from_a"

        @event_listener("custom")
        async def on_event_b(self, value: str) -> Any:
            """Stop propagation after transformation."""
            return StopPropagation

        @event_listener("custom")
        async def on_event_c(self, value: str) -> None:
            """Record if third listener is unexpectedly called."""
            nonlocal third_listener_called
            third_listener_called = True

    manager = _Manager()
    event = manager.create_event("custom")
    external_callback = AsyncMock(return_value=None)
    manager.subscribe("custom", external_callback)

    await manager.dispatch("custom", "raw")

    assert manager.data["custom"] == "raw_from_a"
    assert event.is_set()
    assert not third_listener_called
    external_callback.assert_not_awaited()


async def test_dispatch_stop_propagation_in_first_event_listener() -> None:
    """Test that StopPropagation in the first listener commits original value."""
    second_listener_called = False

    class _Manager(EventManager[Any]):
        """Represent a test event manager with two internal listeners."""

        __slots__ = ()

        @event_listener("custom")
        async def on_event_a(self, value: str) -> Any:
            """Stop propagation immediately."""
            return StopPropagation

        @event_listener("custom")
        async def on_event_b(self, value: str) -> None:
            """Record if second listener is unexpectedly called."""
            nonlocal second_listener_called
            second_listener_called = True

    manager = _Manager()
    event = manager.create_event("custom")
    external_callback = AsyncMock(return_value=None)
    manager.subscribe("custom", external_callback)

    await manager.dispatch("custom", "raw")

    assert manager.data["custom"] == "raw"
    assert event.is_set()
    assert not second_listener_called
    external_callback.assert_not_awaited()


async def test_dispatch_error_in_event_listener(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that an internal listener error leaves Stage 2 and Stage 3 intact."""

    class _Manager(EventManager[Any]):
        """Represent a test event manager with a failing internal listener."""

        __slots__ = ()

        @event_listener("custom")
        async def on_event_a(self, value: str) -> str:
            """Raise an error during event handling."""
            raise OSError("boom")

        @event_listener("custom")
        async def on_event_b(self, value: str) -> str:
            """Transform the value in the second listener."""
            return f"{value}_from_b"

    manager = _Manager()
    event = manager.create_event("custom")
    external_callback = AsyncMock(return_value=None)
    manager.subscribe("custom", external_callback)

    await manager.dispatch("custom", "raw")

    assert "Error in event listener" in caplog.text
    assert manager.data["custom"] == "raw_from_b"
    assert event.is_set()
    external_callback.assert_awaited_once_with("raw_from_b")


async def test_dispatch_error_after_external_replacement(
    event_manager: EventManager, caplog: pytest.LogCaptureFixture
) -> None:
    """Test that an external callback error preserves earlier replacements."""
    observed: list[tuple[Any, Any]] = []

    async def callback1(value: str) -> str:
        """Return a falsy replacement value."""
        return ""

    async def callback2(value: str) -> None:
        """Raise an error after replacement."""
        raise OSError("boom")

    async def callback3(value: str) -> None:
        """Observe the retained replacement value."""
        observed.append((value, event_manager.data["test_key2"]))

    event_manager.subscribe("test_key2", callback1)
    event_manager.subscribe("test_key2", callback2)
    event_manager.subscribe("test_key2", callback3)
    await event_manager.dispatch("test_key2", "initial")

    assert "Error in event listener" in caplog.text
    assert observed == [("", "")]
    assert event_manager.data["test_key2"] == ""


async def test_dispatch_filtered_event_listener() -> None:
    """Test that a filtered internal listener preserves Stage 2 and Stage 3."""
    listener_calls = 0

    class _Manager(EventManager[Any]):
        """Represent a test event manager with a filtered internal listener."""

        __slots__ = ()

        @event_listener(filter=on_change)
        async def on_event_custom(self, value: str) -> str:
            """Transform the value only when it changes."""
            nonlocal listener_calls
            listener_calls += 1
            return f"{value}_transformed"

    manager = _Manager()
    external_callback = AsyncMock(return_value=None)
    manager.subscribe("custom", external_callback)

    await manager.dispatch("custom", "raw")
    await manager.dispatch("custom", "raw")

    assert listener_calls == 1
    assert manager.data["custom"] == "raw"
    external_callback.assert_has_awaits([call("raw_transformed"), call("raw")])


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
    mock_func.__qualname__ = "on_event_test"
    decorator = event_listener()
    decorator(mock_func)
    assert getattr(mock_func, "_on_event") == "test"
    assert not getattr(mock_func, "_on_event_filter")

    # Test without parentheses.
    mock_func.reset_mock()
    mock_func.__qualname__ = "on_event_test2"
    func = event_listener(mock_func)
    assert getattr(func, "_on_event") == "test2"
    assert not getattr(func, "_on_event_filter")

    # Test with name.
    mock_func.reset_mock()
    decorator = event_listener("test3")
    decorator(mock_func)
    assert getattr(mock_func, "_on_event") == "test3"
    assert not getattr(mock_func, "_on_event_filter")

    # Test with filter.
    mock_func.reset_mock()
    mock_filter = Mock()
    decorator = event_listener("test", mock_filter)
    decorator(mock_func)
    assert getattr(mock_func, "_on_event") == "test"
    assert getattr(mock_func, "_on_event_filter") == mock_filter
