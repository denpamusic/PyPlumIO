"""Contains tests for object factory."""

import pytest

from pyplumio.frames.requests import StopMasterRequest
from pyplumio.helpers.factory import factory


def test_get_object() -> None:
    """Test getting object with factory."""
    cls = factory("frames.requests.StopMasterRequest")
    assert isinstance(cls, StopMasterRequest)

    # Check with nonexistent class.
    with pytest.raises(ImportError):
        factory("frames.requests.NonExistent")

    # Check with nonexistent module.
    with pytest.raises(ImportError):
        factory("frames.request.StopMasterRequest")
