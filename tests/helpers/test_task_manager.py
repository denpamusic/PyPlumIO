"""Contains tests for the task manager helper class."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from pyplumio.helpers.task_manager import TaskManager


@pytest.fixture(name="task_manager")
async def fixture_task_manager() -> TaskManager:
    """Return a task manager object."""
    task_manager = TaskManager()
    with patch("asyncio.create_task"):
        task_manager.create_task(Mock())

    return task_manager


def test_create_task(task_manager: TaskManager) -> None:
    """Test creating a task."""
    mock_coro = Mock()
    mock_task = Mock(spec=asyncio.Task)
    with patch("asyncio.create_task", return_value=mock_task) as create_task_mock:
        task_manager.create_task(mock_coro)

    mock_task.add_done_callback.assert_called_once()
    create_task_mock.assert_called_once_with(mock_coro)


def test_cancel_task(task_manager: TaskManager) -> None:
    """Test canceling a task."""
    mock_coro = Mock()
    mock_task = Mock(spec=asyncio.Task)
    with patch("asyncio.create_task", return_value=mock_task):
        task_manager.create_task(mock_coro)

    task_manager.cancel_tasks()
    mock_task.cancel.assert_called_once()


async def test_wait_until_done(task_manager: TaskManager) -> None:
    """Test waiting until all tasks are done."""
    with patch("asyncio.gather", new_callable=AsyncMock) as mock_gather:
        await task_manager.wait_until_done()

    mock_gather.assert_awaited_once_with(*task_manager.tasks, return_exceptions=True)
