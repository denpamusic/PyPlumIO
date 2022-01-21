import pytest

from pyplumio.constants import OUTPUTS
from pyplumio.structures import outputs

_message = bytearray([0x4, 0x0, 0x0, 0x0])


@pytest.fixture()
def outputs_data():
    outputs = {v: False for v in OUTPUTS}
    outputs[OUTPUTS[2]] = True
    return outputs


def test_from_bytes(outputs_data):
    data, offset = outputs.from_bytes(_message)
    assert data == outputs_data
    assert offset == 4
