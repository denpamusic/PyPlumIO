"""Test PyPlumIO outputs structure."""

from typing import Dict

import pytest

from pyplumio.constants import OUTPUTS
from pyplumio.structures import outputs

_message = bytearray([0x4, 0x0, 0x0, 0x0])


@pytest.fixture(name="outputs_data")
def fixture_outputs_data() -> Dict[str, bool]:
    """Return test outputs data."""
    outputs = {v: False for v in OUTPUTS}
    outputs[OUTPUTS[2]] = True
    return outputs


def test_from_bytes(outputs_data) -> None:
    """Test conversion from bytes."""
    data, offset = outputs.from_bytes(_message)
    assert data == outputs_data
    assert offset == 4
