"""Contains tests for the timeout decorator class."""

import asyncio
from unittest.mock import Mock, patch

import pytest

from pyplumio.helpers.timeout import timeout


@patch("asyncio.wait_for", side_effect=("test", asyncio.TimeoutError))
async def test_timeout(mock_wait_for) -> None:
    """Test a timeout decorator."""
    # Mock function to pass to the decorator.
    mock_func = Mock(return_value="test")

    # Call the decorator.
    timeout_decorator = timeout(10)
    wrapper = timeout_decorator(mock_func)
    result = await wrapper("test_arg", kwarg="test_kwarg")
    assert result == "test"
    mock_wait_for.assert_awaited_once_with(mock_func.return_value, timeout=10)
    mock_func.assert_called_once_with("test_arg", kwarg="test_kwarg")

    # Test behavior when a timeout occurs.
    mock_func.reset_mock()
    timeout_decorator = timeout(10)
    wrapper = timeout_decorator(mock_func)
    with pytest.raises(asyncio.TimeoutError):
        await wrapper("test_arg", kwarg="test_kwarg")
