from pyplumio.structures import var_string

_message = bytearray([0xA, 0x45, 0x4D, 0x33, 0x35, 0x30, 0x50, 0x32, 0x2D, 0x5A, 0x46])


def test_from_bytes() -> None:
    data, offset = var_string.from_bytes(_message)
    assert data == "EM350P2-ZF"
    assert offset == 12
