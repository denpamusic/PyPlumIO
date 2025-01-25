"""Contains tests for the object factory."""

import pytest

from pyplumio.frames import Request
from pyplumio.frames.requests import StopMasterRequest
from pyplumio.helpers.factory import create_instance


async def test_get_object() -> None:
    """Test getting an object via class path."""
    cls = await create_instance("frames.requests.StopMasterRequest", cls=Request)
    assert isinstance(cls, StopMasterRequest)


async def test_get_object_with_incorrect_base_class() -> None:
    """Test getting an object via class path with incorrect base class."""
    with pytest.raises(TypeError) as exc_info:
        await create_instance("frames.responses.UIDResponse", cls=Request)

    assert str(exc_info.value) == (
        "Expected instance of 'Request', but got 'UIDResponse' from 'UIDResponse'"
    )


async def test_get_object_with_nonexistent_class() -> None:
    """Test getting an object via class path for nonexistent class."""
    with pytest.raises(AttributeError):
        await create_instance("frames.requests.NonExistent", cls=Request)


async def test_get_object_with_nonexistent_module() -> None:
    """Test getting an object via class path for a class within nonexistent module."""
    with pytest.raises(ModuleNotFoundError):
        await create_instance("frames.request.StopMasterRequest", cls=Request)
