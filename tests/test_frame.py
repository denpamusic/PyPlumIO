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


def test_passing_frame_type():
    frame = Frame(type_=ProgramVersion.type_)
    assert frame.type_ == ProgramVersion.type_


def test_base_class_with_default_params():
    frame = Frame(type_=ProgramVersion.type_)
    assert frame.recipient == BROADCAST_ADDRESS
    assert frame.message == b""
    assert frame.sender == ECONET_ADDRESS
    assert frame.sender_type == ECONET_TYPE
    assert frame.econet_version == ECONET_VERSION


def test_frame_length_without_data():
    frame = Frame(type_=ProgramVersion.type_)
    assert frame.length == HEADER_SIZE + 3
    assert len(frame) == HEADER_SIZE + 3


def test_get_header():
    frame = Frame(type_=ProgramVersion.type_)
    assert frame.header == b"\x68\x0a\x00\x00\x56\x30\x05"


def test_frame_type_check():
    frame = ProgramVersion(recipient=BROADCAST_ADDRESS)
    assert frame.is_type(ProgramVersion)


def test_base_class_raises_not_implemented_on_data():
    frame = Frame(type_=ProgramVersion.type_)
    with pytest.raises(NotImplementedError):
        frame.data()


def test_base_class_raises_not_implemented_on_parse():
    frame = Frame(type_=ProgramVersion.type_)
    with pytest.raises(NotImplementedError):
        frame.parse_message(b"\x00")


def test_base_class_raises_not_implemented_on_create():
    frame = Frame(type_=ProgramVersion.type_)
    with pytest.raises(NotImplementedError):
        frame.create_message()
