"""Contains tests for current alerts structure."""

from pyplumio.const import ATTR_ALERTS
from pyplumio.structures.current_alerts import from_bytes

_message = bytearray.fromhex("03101112")
_data = {ATTR_ALERTS: [3, 16, 17]}


def test_from_bytes() -> None:
    """Test conversion from bytes."""
    data, offset = from_bytes(_message)
    assert data == _data
    assert offset == 4
