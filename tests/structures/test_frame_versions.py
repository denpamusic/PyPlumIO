"""Contains tests for frame version structure."""

from pyplumio.structures.frame_versions import FRAME_VERSIONS, from_bytes

_message = bytearray.fromhex("075500005400006108003DECF43601006401004000")
_data = {FRAME_VERSIONS: {85: 0, 84: 0, 97: 8, 61: 62700, 54: 1, 100: 1, 64: 0}}


def test_from_bytes():
    """Test conversion from bytes."""
    data, offset = from_bytes(_message)
    assert data == _data
    assert offset == 22
