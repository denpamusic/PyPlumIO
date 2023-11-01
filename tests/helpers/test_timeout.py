"""Contains tests for the timeout decorator class."""

import asyncio
import logging
from unittest.mock import AsyncMock, Mock, patch

import pytest

from pyplumio.helpers.timeout import timeout


@patch("asyncio.wait_for", new_callable=AsyncMock, side_effect=(asyncio.TimeoutError))
async def test_timeout(mock_wait_for, caplog) -> None:
    """Test a timeout decorator."""
    # Mock function to pass to the decorator.
    mock_func = Mock()
    mock_func.return_value = "test"
    mock_func.__name__ = "func_name"

    # Call the decorator.
    decorator = timeout(10, raise_exception=False)
    wrapper = decorator(mock_func)
    with caplog.at_level(logging.WARNING):
        result = await wrapper("test_arg", kwarg="test_kwarg")

    assert result is None
    assert "Function 'func_name' timed out" in caplog.text
    assert "func_name" in caplog.text
    mock_wait_for.assert_awaited_once_with("test", timeout=10)
    mock_func.assert_called_once_with("test_arg", kwarg="test_kwarg")

    # Check with raise_exception set to true.
    decorator = timeout(10, raise_exception=True)
    wrapper = decorator(mock_func)
    with pytest.raises(asyncio.TimeoutError):
        await wrapper("test_arg", kwarg="test_kwarg")
