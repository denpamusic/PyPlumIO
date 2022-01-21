from pyplumio.constants import (
    DATA_CIRCULATION_PUMP_FLAG,
    DATA_CO_PUMP_FLAG,
    DATA_CWU_PUMP_FLAG,
    DATA_SOLAR_PUMP_FLAG,
)
from pyplumio.structures import output_flags

_message = bytearray([0xBF, 0x0, 0x0, 0x0])
_data = {
    DATA_CO_PUMP_FLAG: True,
    DATA_CWU_PUMP_FLAG: True,
    DATA_CIRCULATION_PUMP_FLAG: True,
    DATA_SOLAR_PUMP_FLAG: False,
}


def test_from_bytes():
    data, offset = output_flags.from_bytes(_message)
    assert data == _data
    assert offset == 4
