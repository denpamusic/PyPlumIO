"""Contains tests for lambda structure."""

from pyplumio.const import ATTR_LAMBDA_SENSOR
from pyplumio.structures.lambda_sensor import (
    LAMBDA_LEVEL,
    LAMBDA_STATUS,
    LAMBDA_TARGET,
    from_bytes,
)

_empty = bytearray.fromhex("FF")
_message = bytearray.fromhex("01022800")
_data = {LAMBDA_STATUS: 1, LAMBDA_TARGET: 2, LAMBDA_LEVEL: 40}


def test_from_bytes_empty():
    """Test conversion from bytes with empty data."""
    data, offset = from_bytes(_empty)
    assert data == {ATTR_LAMBDA_SENSOR: {}}
    assert offset == 1


def test_from_bytes():
    """Test conversion from bytes."""
    data, offset = from_bytes(_message)
    assert data == {ATTR_LAMBDA_SENSOR: _data}
    assert offset == 4
