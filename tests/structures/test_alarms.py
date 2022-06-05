"""Test PyPlumIO alarms structure."""

from pyplumio.structures.alarms import ALARMS, from_bytes

_message = bytearray.fromhex("03101112")
_data = {ALARMS: [3, 16, 17]}


def test_from_bytes() -> None:
    """Test conversion from bytes."""
    data, offset = from_bytes(_message)
    assert data == _data
    assert offset == 4
