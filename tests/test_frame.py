import pytest

from pyplumio.constants import (
    BROADCAST_ADDRESS,
    ECONET_ADDRESS,
    ECONET_TYPE,
    ECONET_VERSION,
    HEADER_SIZE,
)
from pyplumio.frame import Frame
from pyplumio.frames.requests import ProgramVersion


@pytest.fixture
def frame():
    return Frame(type_=ProgramVersion.type_)


def test_passing_frame_type(frame):
    assert frame.type_ == ProgramVersion.type_


def test_base_class_with_default_params(frame):
    assert frame.recipient == BROADCAST_ADDRESS
    assert frame.message == b""
    assert frame.sender == ECONET_ADDRESS
    assert frame.sender_type == ECONET_TYPE
    assert frame.econet_version == ECONET_VERSION


def test_base_class_with_message():
    frame = Frame(type_=ProgramVersion.type_, message=b"\xB0\x0B")
    assert frame.message == b"\xB0\x0B"


def test_frame_length_without_data(frame):
    assert frame.length == HEADER_SIZE + 3
    assert len(frame) == HEADER_SIZE + 3


def test_get_header(frame):
    assert frame.header == b"\x68\x0a\x00\x00\x56\x30\x05"


def test_to_bytes():
    frame = Frame(type_=ProgramVersion.type_, message=b"\xB0\x0B")
    assert frame.to_bytes() == b"\x68\x0C\x00\x00\x56\x30\x05\x40\xB0\x0B\xFC\x16"


def test_to_hex():
    frame = Frame(type_=ProgramVersion.type_, message=b"\xB0\x0B")
    hex = ["68", "0C", "00", "00", "56", "30", "05", "40", "B0", "0B", "FC", "16"]
    assert frame.to_hex() == hex


def test_frame_type_check():
    frame = ProgramVersion(recipient=BROADCAST_ADDRESS)
    assert frame.is_type(ProgramVersion)


def test_base_class_raises_not_implemented_on_data(frame):
    with pytest.raises(NotImplementedError):
        frame.data()


def test_base_class_raises_not_implemented_on_parse(frame):
    with pytest.raises(NotImplementedError):
        frame.parse_message(b"\x00")


def test_base_class_raises_not_implemented_on_create(frame):
    with pytest.raises(NotImplementedError):
        frame.create_message()


def test_base_class_repr(frame):
    repr_ = """Frame(
    type = 64,
    recipient = 0,
    message = bytearray(b''),
    sender = 86,
    sender_type = 48,
    econet_version = 5,
    data = None
)
""".strip()
    assert repr(frame) == repr_
