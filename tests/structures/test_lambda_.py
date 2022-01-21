from pyplumio.constants import DATA_LAMBDA_LEVEL, DATA_LAMBDA_STATUS, DATA_LAMBDA_TARGET
from pyplumio.structures import lambda_

_empty = bytearray([0xFF])
_message = bytearray([0x1, 0x2, 0x28, 0x0])
_data = {DATA_LAMBDA_STATUS: 1, DATA_LAMBDA_TARGET: 2, DATA_LAMBDA_LEVEL: 40}


def test_from_bytes_empty():
    data, offset = lambda_.from_bytes(_empty)
    assert data == {}
    assert offset == 1


def test_from_bytes():
    data, offset = lambda_.from_bytes(_message)
    assert data == _data
    assert offset == 4
