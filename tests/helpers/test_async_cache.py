"""Contains tests for the simple async cache."""

from unittest.mock import AsyncMock, patch

import pytest

from pyplumio.helpers.async_cache import AsyncCache, acache


@pytest.fixture(name="async_cache")
def fixture_async_cache():
    """Fixture for the async cache."""
    return AsyncCache()


async def test_async_cache_get(async_cache: AsyncCache):
    """Test the get method of the async cache."""
    mock_coro = AsyncMock(return_value="test_value")
    cache_key = "test_key"

    assert cache_key not in async_cache.cache
    result = await async_cache.get(cache_key, mock_coro)
    assert result == "test_value"
    assert cache_key in async_cache.cache

    # Verify the cached value is returned on subsequent calls
    mock_coro.reset_mock()
    cached_result = await async_cache.get(cache_key, mock_coro)
    assert cached_result == "test_value"
    mock_coro.assert_not_called()


async def test_acache():
    """Test an acache decorator."""
    # Mock function to pass to the decorator.
    mock_coro = AsyncMock(return_value="test_value")
    mock_coro.__qualname__ = "test_coro"

    # Call the decorator.
    decorator = acache(mock_coro)
    with patch("pyplumio.helpers.async_cache.AsyncCache.get") as mock_get:
        await decorator()

    # Check that get function was execute with correct parameters.
    mock_get.assert_awaited_once()
    get_call = mock_get.call_args[0]
    key, func = get_call
    assert key == "unittest.mock.test_coro:():{}"
    assert await func() == "test_value"
