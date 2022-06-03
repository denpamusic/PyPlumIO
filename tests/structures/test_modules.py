"""Test PyPlumIO modules structure."""

from pyplumio.constants import DATA_MODULES
from pyplumio.helpers.product_info import ConnectedModules
from pyplumio.structures.modules import from_bytes

_message = bytearray([0x1, 0xD, 0x5, 0x5A, 0x1, 0xFF, 0xFF, 0xFF, 0xFF, 0x2, 0x3, 0x2B])
_data = {DATA_MODULES: ConnectedModules(module_a="1.13.5.Z1", module_panel="2.3.43")}


def test_from_bytes() -> None:
    """Test conversion from bytes."""
    data, offset = from_bytes(_message)
    assert data == _data
    assert offset == 12
