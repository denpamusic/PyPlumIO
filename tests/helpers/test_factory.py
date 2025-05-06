"""Contains tests for the object factory."""

from __future__ import annotations

from typing import Literal

import pytest

from pyplumio.frames import Frame, Request, Response
from pyplumio.frames.messages import RegulatorDataMessage
from pyplumio.frames.requests import StopMasterRequest
from pyplumio.frames.responses import UIDResponse
from pyplumio.helpers.factory import create_instance
from tests.conftest import RAISES


@pytest.mark.parametrize(
    ("path", "base", "expected", "error_pattern"),
    [
        ("frames.requests.StopMasterRequest", Request, StopMasterRequest, None),
        ("frames.responses.UIDResponse", Response, UIDResponse, None),
        ("frames.messages.RegulatorDataMessage", Frame, RegulatorDataMessage, None),
        ("frames.responses.UIDResponse", Request, RAISES, "Expected instance"),
        ("frames.requests.NonExistent", Request, RAISES, "no attribute"),
        ("frames.request.StopMasterRequest", Request, RAISES, "No module"),
    ],
)
async def test_create_instance(
    path: str,
    base: type,
    expected: type | Literal["raises"],
    error_pattern: str | None,
) -> None:
    """Test creating an instance of class."""
    if expected == RAISES:
        with pytest.raises(
            (TypeError, AttributeError, ModuleNotFoundError), match=error_pattern
        ):
            await create_instance(path, cls=base)
    else:
        assert isinstance(await create_instance(path, cls=base), expected)
