"""Test PyPlumIO device parameters structure."""

from pyplumio.constants import DATA_BOILER_PARAMETERS
from pyplumio.structures.boiler_parameters import BOILER_PARAMETERS, from_bytes

_message = bytearray.fromhex("000005503D643C294C28143BFFFFFF1401FA")
_message_empty = bytearray.fromhex("000000")
_data = {
    BOILER_PARAMETERS[0]: (BOILER_PARAMETERS[0], 80, 61, 100),
    BOILER_PARAMETERS[1]: (BOILER_PARAMETERS[1], 60, 41, 76),
    BOILER_PARAMETERS[2]: (BOILER_PARAMETERS[2], 40, 20, 59),
    BOILER_PARAMETERS[4]: (BOILER_PARAMETERS[4], 20, 1, 250),
}


def test_from_bytes() -> None:
    """Test conversion from bytes."""
    data, offset = from_bytes(_message)
    assert data == {DATA_BOILER_PARAMETERS: _data}
    assert offset == 18


def test_from_bytes_with_no_params() -> None:
    """Test conversion from bytes with no data."""
    data, offset = from_bytes(_message_empty)
    assert data == {DATA_BOILER_PARAMETERS: {}}
    assert offset == 3
