"""Contains tests for outputs structure."""

from typing import Dict

import pytest

from pyplumio.structures.outputs import OUTPUTS, from_bytes

_message = bytearray.fromhex("04000000")


@pytest.fixture(name="outputs_data")
def fixture_outputs_data() -> Dict[str, bool]:
    """Return test outputs data."""
    outputs = {v: False for v in OUTPUTS}
    outputs[OUTPUTS[2]] = True
    return outputs


def test_from_bytes(outputs_data: Dict[str, bool]) -> None:
    """Test conversion from bytes."""
    data, offset = from_bytes(_message)
    assert data == outputs_data
    assert offset == 4
