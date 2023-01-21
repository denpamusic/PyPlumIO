"""Contains tests for task manager."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

from pyplumio.helpers.task_manager import TaskManager


@patch("asyncio.gather", new_callable=AsyncMock)
async def test_task_manager(mock_gather) -> None:
    """Test task manager."""
    task_manager = TaskManager()

    mock_coro = Mock()
    mock_task = Mock(spec=asyncio.Task)
    with patch("asyncio.create_task", return_value=mock_task) as create_task_mock:
        task_manager.create_task(mock_coro)

    create_task_mock.assert_called_once_with(mock_coro)
    mock_task.add_done_callback.assert_called_once()

    # Check that task get cancelled.
    task_manager.cancel_tasks()
    mock_task.cancel.assert_called_once()

    # Check awaiting tasks.
    await task_manager.wait_until_done()
    mock_gather.assert_awaited_once_with(*task_manager.tasks, return_exceptions=True)

    # Test creating event.
    event = task_manager.create_event("test")
    assert event == task_manager.create_event("test")
    assert "test" in task_manager.events
    assert not task_manager.events["test"].is_set()
    task_manager.set_event("test")
    assert task_manager.events["test"].is_set()
