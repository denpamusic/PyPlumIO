from pyplumio.constants import (
    MODULE_A,
    MODULE_B,
    MODULE_C,
    MODULE_ECOSTER,
    MODULE_LAMBDA,
    MODULE_PANEL,
)
from pyplumio.structures import modules

_message = bytearray([0x1, 0xD, 0x5, 0x5A, 0x1, 0xFF, 0xFF, 0xFF, 0xFF, 0x2, 0x3, 0x2B])
_data = {
    MODULE_PANEL: "1.13.5.Z1",
    MODULE_A: None,
    MODULE_B: None,
    MODULE_C: None,
    MODULE_LAMBDA: None,
    MODULE_ECOSTER: "2.3.43",
}


def test_from_bytes():
    data, offset = modules.from_bytes(_message)
    assert data == _data
    assert offset == 12
