"""Test PyPlumIO base frame."""

from typing import ClassVar, Tuple

import pytest

from pyplumio.const import AddressTypes, FrameTypes
from pyplumio.exceptions import UnknownFrameError
from pyplumio.frames import (
    ECONET_TYPE,
    ECONET_VERSION,
    HEADER_SIZE,
    Request,
    Response,
    get_frame_handler,
)
from pyplumio.frames.responses import ProgramVersionResponse


class RequestFrame(Request):
    """Test request class."""

    frame_type: ClassVar[int] = FrameTypes.REQUEST_PROGRAM_VERSION


class ResponseFrame(Response):
    """Test response class."""

    frame_type: ClassVar[int] = FrameTypes.RESPONSE_PROGRAM_VERSION


@pytest.fixture(name="request_frame")
def fixture_request_frame() -> Request:
    """Return program version request."""
    return RequestFrame()


@pytest.fixture(name="response_frame")
def fixture_response_frame() -> Response:
    """Return program version response."""
    return ResponseFrame()


@pytest.fixture(name="frames")
def fixture_frames(
    request_frame: Request, response_frame: Response
) -> Tuple[Request, Response]:
    """Return request and response frames as a tuple."""
    return (request_frame, response_frame)


@pytest.fixture(name="types")
def fixture_types() -> Tuple[int, int]:
    """Return request and response types as a tuple."""
    return (FrameTypes.REQUEST_PROGRAM_VERSION, FrameTypes.RESPONSE_PROGRAM_VERSION)


def test_decode_create_message(frames: Tuple[Request, Response]) -> None:
    """Test creating and decoding message."""
    for frame in frames:
        assert frame.create_message(data={}) == bytearray()
        assert frame.decode_message(message=bytearray()) == {}


def test_get_frame_handler() -> None:
    """Test getting frame handler."""
    assert get_frame_handler(0x18) == "frames.requests.StopMasterRequest"
    with pytest.raises(UnknownFrameError):
        get_frame_handler(0x0)


def test_passing_frame_type(
    frames: Tuple[Request, Response], types: Tuple[int, int]
) -> None:
    """Test getting frame type."""
    for index, frame in enumerate(frames):
        assert frame.frame_type == types[index]


def test_default_params(frames: Tuple[Request, Response]) -> None:
    """Test frame attributes."""
    for frame in frames:
        assert frame.recipient == AddressTypes.BROADCAST
        assert frame.message == b""
        assert frame.sender == AddressTypes.ECONET
        assert frame.sender_type == ECONET_TYPE
        assert frame.econet_version == ECONET_VERSION


def test_frame_length_without_data(frames: Tuple[Request, Response]) -> None:
    """Test frame length without any data."""
    for frame in frames:
        assert frame.length == HEADER_SIZE + 3
        assert len(frame) == HEADER_SIZE + 3


def test_get_header(frames: Tuple[Request, Response]) -> None:
    """Test getting frame header as bytes."""
    for frame in frames:
        assert frame.header == b"\x68\x0a\x00\x00\x56\x30\x05"


def test_base_class_with_message() -> None:
    """Test base request class with message."""
    frame = RequestFrame(message=bytearray.fromhex("B00B"))
    assert frame.message == b"\xB0\x0B"


def test_to_bytes() -> None:
    """Test conversion to bytes."""
    frame = RequestFrame(message=bytearray(b"\xB0\x0B"))
    assert frame.bytes == b"\x68\x0C\x00\x00\x56\x30\x05\x40\xB0\x0B\xFC\x16"


def test_to_hex() -> None:
    """Test conversion to hex."""
    frame = RequestFrame(message=bytearray(b"\xB0\x0B"))
    hex_data = ["68", "0C", "00", "00", "56", "30", "05", "40", "B0", "0B", "FC", "16"]
    assert frame.hex == hex_data


def test_equality() -> None:
    """Test equality check."""
    assert ProgramVersionResponse() == ProgramVersionResponse()


def test_request_framerepr(request_frame: Request) -> None:
    """Test serialiazible request representation."""
    repr_string = (
        "RequestFrame(recipient=<AddressTypes.BROADCAST: 0>, sender=<AddressTypes.ECONET: 86>, sender_type=48, econet_version=5, "
        + "message=bytearray(b''), data={})"
    )
    assert repr(request_frame) == repr_string


def test_response_repr(response_frame: Response) -> None:
    """Test serialiazible response representation."""
    repr_string = (
        "ResponseFrame(recipient=<AddressTypes.BROADCAST: 0>, sender=<AddressTypes.ECONET: 86>, sender_type=48, econet_version=5, "
        + "message=bytearray(b''), data={})"
    )
    assert repr(response_frame) == repr_string
