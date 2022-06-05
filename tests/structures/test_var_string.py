from pyplumio.structures import var_string

_message = bytearray.fromhex("0A454D33353050322D5A46")


def test_from_bytes() -> None:
    data, offset = var_string.from_bytes(_message)
    assert data == "EM350P2-ZF"
    assert offset == 12
