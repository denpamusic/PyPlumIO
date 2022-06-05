"""Test PyPlumIO modules structure."""

from pyplumio.constants import DATA_MODULES
from pyplumio.helpers.product_info import ConnectedModules
from pyplumio.structures.modules import from_bytes

_message = bytearray.fromhex("010D055A01FFFFFFFF02032B")
_data = {DATA_MODULES: ConnectedModules(module_a="1.13.5.Z1", module_panel="2.3.43")}


def test_from_bytes() -> None:
    """Test conversion from bytes."""
    data, offset = from_bytes(_message)
    assert data == _data
    assert offset == 12
