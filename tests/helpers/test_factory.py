"""Contains tests for the object factory."""

import pytest

from pyplumio.frames.requests import StopMasterRequest
from pyplumio.helpers.factory import factory


def test_get_object() -> None:
    """Test getting an object via class path."""
    cls = factory("frames.requests.StopMasterRequest")
    assert isinstance(cls, StopMasterRequest)


def test_get_object_with_nonexistent_class() -> None:
    """Test getting an object via class path for nonexistent class."""
    with pytest.raises(AttributeError):
        factory("frames.requests.NonExistent")


def test_get_object_with_nonexistent_module() -> None:
    """Test getting an object via class path for a class within
    a nonexistent module.
    """
    with pytest.raises(ModuleNotFoundError):
        factory("frames.request.StopMasterRequest")
