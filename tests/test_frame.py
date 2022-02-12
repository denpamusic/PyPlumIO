import pytest

from pyplumio import requests, responses
from pyplumio.frame import (
    BROADCAST_ADDRESS,
    ECONET_ADDRESS,
    ECONET_TYPE,
    ECONET_VERSION,
    HEADER_SIZE,
    Request,
    Response,
)


@pytest.fixture
def request_():
    return Request(type_=requests.ProgramVersion.type_)


@pytest.fixture
def response():
    return Response(type_=responses.ProgramVersion.type_)


@pytest.fixture
def frames(request_, response):
    return [request_, response]


@pytest.fixture
def types():
    return [requests.ProgramVersion.type_, responses.ProgramVersion.type_]


def test_passing_frame_type(frames, types):
    for index, frame in enumerate(frames):
        assert frame.type_ == types[index]


def test_default_params(frames):
    for frame in frames:
        assert frame.recipient == BROADCAST_ADDRESS
        assert frame.message == b""
        assert frame.sender == ECONET_ADDRESS
        assert frame.sender_type == ECONET_TYPE
        assert frame.econet_version == ECONET_VERSION


def test_frame_length_without_data(frames):
    for frame in frames:
        assert frame.length == HEADER_SIZE + 3
        assert len(frame) == HEADER_SIZE + 3


def test_get_header(frames):
    for frame in frames:
        assert frame.header == b"\x68\x0a\x00\x00\x56\x30\x05"


def test_base_class_with_message():
    frame = Request(type_=requests.ProgramVersion.type_, message=b"\xB0\x0B")
    assert frame.message == b"\xB0\x0B"


def test_bytes():
    frame = Request(type_=requests.ProgramVersion.type_, message=b"\xB0\x0B")
    assert frame.bytes == b"\x68\x0C\x00\x00\x56\x30\x05\x40\xB0\x0B\xFC\x16"


def test_hex():
    frame = Request(type_=requests.ProgramVersion.type_, message=b"\xB0\x0B")
    hex = ["68", "0C", "00", "00", "56", "30", "05", "40", "B0", "0B", "FC", "16"]
    assert frame.hex == hex


def test_request_repr(request_):
    repr_ = """Request(
    type = 64,
    recipient = 0,
    message = bytearray(b''),
    sender = 86,
    sender_type = 48,
    econet_version = 5,
    data = None
)
""".strip()
    assert repr(request_) == repr_


def test_response_repr(response):
    repr_ = """Response(
    type = 192,
    recipient = 0,
    message = bytearray(b''),
    sender = 86,
    sender_type = 48,
    econet_version = 5,
    data = None
)
""".strip()
    assert repr(response) == repr_
