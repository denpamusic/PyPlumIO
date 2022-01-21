from pyplumio.structures import uid

_message = bytearray(
    [0xB, 0x0, 0x16, 0x0, 0x11, 0xD, 0x38, 0x33, 0x38, 0x36, 0x55, 0x39, 0x5A]
)


def test_from_bytes():
    data, offset = uid.from_bytes(_message)
    assert data == "D251PAKR3GCPZ1K8G05G0"
    assert offset == 12
