"""Contains tests for the abstract frame class."""

from __future__ import annotations

import pytest
from tests.conftest import RAISES

from pyplumio.const import DeviceType, FrameType
from pyplumio.exceptions import UnknownFrameError
from pyplumio.frames import (
    ECONET_TYPE,
    ECONET_VERSION,
    Request,
    Response,
    get_frame_handler,
    struct_header,
)
from pyplumio.frames.responses import ProgramVersionResponse
from pyplumio.structures.program_version import ATTR_VERSION, VersionInfo


class RequestFrame(Request):
    """Representation of a request frame."""

    frame_type = FrameType.REQUEST_PROGRAM_VERSION


class ResponseFrame(Response):
    """Representation of a response frame."""

    frame_type = FrameType.RESPONSE_PROGRAM_VERSION


@pytest.fixture(name="request_frame")
def fixture_request_frame() -> Request:
    """Return a request frame object."""
    return RequestFrame(foo=0)


@pytest.fixture(name="response_frame")
def fixture_response_frame() -> Response:
    """Return a response frame object."""
    return ResponseFrame(foo=0)


@pytest.fixture(name="frames")
def fixture_frames(
    request_frame: Request, response_frame: Response
) -> tuple[Request, Response]:
    """Return both request and response frame objects as a tuple."""
    return (request_frame, response_frame)


@pytest.fixture(name="types")
def fixture_types() -> tuple[int, int]:
    """Return request and response types as a tuple."""
    return (FrameType.REQUEST_PROGRAM_VERSION, FrameType.RESPONSE_PROGRAM_VERSION)


def test_decode_create_message(frames: tuple[Request, Response]) -> None:
    """Test creating and decoding frame message."""
    for frame in frames:
        assert frame.create_message(data={}) == bytearray()
        assert frame.decode_message(message=bytearray()) == {}


@pytest.mark.parametrize(
    ("frame_type", "handler"),
    [
        (FrameType.REQUEST_STOP_MASTER, "frames.requests.StopMasterRequest"),
        (FrameType.RESPONSE_ECOMAX_CONTROL, "frames.responses.EcomaxControlResponse"),
        (FrameType.MESSAGE_REGULATOR_DATA, "frames.messages.RegulatorDataMessage"),
        (99, RAISES),
    ],
)
def test_get_frame_handler(frame_type: FrameType | int, handler: str) -> None:
    """Test getting a frame handler."""
    if handler == RAISES:
        with pytest.raises(UnknownFrameError):
            get_frame_handler(frame_type)
    else:
        assert get_frame_handler(frame_type) == handler


def test_passing_frame_type(
    frames: tuple[Request, Response], types: tuple[int, int]
) -> None:
    """Test getting a frame type."""
    for index, frame in enumerate(frames):
        assert frame.frame_type == types[index]


def test_frame_attributes(frames: tuple[Request, Response]) -> None:
    """Test accessing frame attributes."""
    for frame in frames:
        assert frame.recipient == DeviceType.ALL
        assert frame.message == b""
        assert frame.sender == DeviceType.ECONET
        assert frame.econet_type == ECONET_TYPE
        assert frame.econet_version == ECONET_VERSION
        assert frame.data == {"foo": 0}


def test_frame_length_without_data(frames: tuple[Request, Response]) -> None:
    """Test a frame length without any data."""
    for frame in frames:
        assert frame.length == struct_header.size + 3
        assert len(frame) == struct_header.size + 3


def test_get_header(frames: tuple[Request, Response]) -> None:
    """Test getting a frame header as bytes."""
    for frame in frames:
        assert frame.header == b"\x68\x0a\x00\x00\x56\x30\x05"


def test_base_class_with_message() -> None:
    """Test base request class with a message."""
    frame = RequestFrame(message=bytearray.fromhex("B00B"))
    assert frame.message == b"\xb0\x0b"


def test_to_bytes() -> None:
    """Test conversion to bytes."""
    frame = RequestFrame(message=bytearray(b"\xb0\x0b"))
    assert frame.bytes == b"\x68\x0c\x00\x00\x56\x30\x05\x40\xb0\x0b\xfc\x16"


def test_to_hex() -> None:
    """Test conversion to hex."""
    frame = RequestFrame(message=bytearray(b"\xb0\x0b"))
    hex_data = "680c000056300540b00bfc16"
    assert frame.hex() == hex_data


def test_equality() -> None:
    """Test frame objects equality."""
    assert ProgramVersionResponse() == ProgramVersionResponse()
    assert ProgramVersionResponse().__eq__("melon") is NotImplemented


def test_data_setter():
    """Test frame data setter."""
    frame = ProgramVersionResponse(data={ATTR_VERSION: VersionInfo(software="1.0.0")})
    assert frame.message.hex() == "ffff057a0000000001000000000056"
    frame.data = {ATTR_VERSION: VersionInfo(software="1.0.0", struct_version=6)}
    assert frame.message.hex() == "ffff067a0000000001000000000056"


def test_message_setter():
    """Test frame message setter."""
    frame = ProgramVersionResponse(
        message=bytearray.fromhex("ffff057a00000000000004000f0056")
    )
    assert frame.data[ATTR_VERSION].struct_version == 5
    frame.message = bytearray.fromhex("ffff067a00000000000004000f0056")
    assert frame.data[ATTR_VERSION].struct_version == 6


def test_request_repr(request_frame: Request) -> None:
    """Test a request class serialiazible representation."""
    assert repr(request_frame) == (
        "RequestFrame("
        "recipient=<DeviceType.ALL: 0>, "
        "sender=<DeviceType.ECONET: 86>, "
        "econet_type=48, "
        "econet_version=5, "
        "message=bytearray(b''), "
        "data={'foo': 0})"
    )


def test_response_repr(response_frame: Response) -> None:
    """Test a response class serialiazible representation."""
    assert repr(response_frame) == (
        "ResponseFrame("
        "recipient=<DeviceType.ALL: 0>, "
        "sender=<DeviceType.ECONET: 86>, "
        "econet_type=48, "
        "econet_version=5, "
        "message=bytearray(b''), "
        "data={'foo': 0})"
    )
