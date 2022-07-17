"""Contains tests for alarms structure."""

from pyplumio.const import ATTR_ALARMS
from pyplumio.structures.alarms import from_bytes

_message = bytearray.fromhex("03101112")
_data = {ATTR_ALARMS: [3, 16, 17]}


def test_from_bytes() -> None:
    """Test conversion from bytes."""
    data, offset = from_bytes(_message)
    assert data == _data
    assert offset == 4
