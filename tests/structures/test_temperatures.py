"""Contains tests for temperatures structure."""

from pyplumio.structures.temperatures import TEMPERATURES, from_bytes

_message = bytearray.fromhex(
    "0700A455784201901BCF410208CA5F420300907BBF05DF9D4D4207FFFFFFFF08FFFFFFFF"
)
_data = {
    TEMPERATURES[0]: 62.08363342285156,
    TEMPERATURES[1]: 25.888458251953125,
    TEMPERATURES[2]: 55.947296142578125,
    TEMPERATURES[3]: -0.982666015625,
    TEMPERATURES[5]: 51.404170989990234,
}


def test_from_bytes() -> None:
    """Test conversion from bytes."""
    data, offset = from_bytes(_message)
    assert data == _data
    assert offset == 36
