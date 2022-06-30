"""Contains tests for factory helper."""

import pytest

from pyplumio.frames.requests import StopMaster
from pyplumio.helpers.factory import factory


def test_get_object() -> None:
    """Test getting object with factory."""
    cls = factory("frames.requests.StopMaster")
    assert isinstance(cls, StopMaster)

    # Check with nonexistent class.
    with pytest.raises(ImportError):
        factory("frames.requests.StopMaste")

    # Check with nonexistent module.
    with pytest.raises(ImportError):
        factory("frames.request.StopMaster")
