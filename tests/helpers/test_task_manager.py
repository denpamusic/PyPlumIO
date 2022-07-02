"""Contains tests for task manager."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from pyplumio.helpers.task_manager import TaskManager


@pytest.fixture(name="task_manager")
def fixture_task_manager() -> TaskManager:
    """Return task manager instance."""
    return TaskManager()


@patch("asyncio.gather", new_callable=AsyncMock)
async def test_task_manager(mock_gather, task_manager: TaskManager) -> None:
    """Test task manager."""
    mock_coro = Mock()
    mock_task = Mock()
    with patch("asyncio.create_task", return_value=mock_task) as create_task_mock:
        task_manager.create_task(mock_coro)

    create_task_mock.assert_called_once_with(mock_coro)
    mock_task.add_done_callback.assert_called_once()

    # Check that task get cancelled.
    task_manager.cancel_tasks()
    mock_task.cancel.assert_called_once()

    # Check awaiting tasks.
    await task_manager.wait_for_tasks()
    mock_gather.assert_awaited_once_with(*task_manager.tasks, return_exceptions=True)
