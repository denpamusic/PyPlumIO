"""Test PyPlumIO response frames."""

from typing import Dict

from pyplumio.const import ATTR_SCHEMA, ATTR_STATE, DeviceTypes, FrameTypes
from pyplumio.frames.responses import (
    AlertsResponse,
    DataSchemaResponse,
    DeviceAvailableResponse,
    EcomaxParametersResponse,
    MixerParametersResponse,
    PasswordResponse,
    ProgramVersionResponse,
    SchedulesResponse,
    UIDResponse,
)
from pyplumio.helpers.data_types import Byte
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures.data_schema import REGDATA_SCHEMA


def test_responses_type() -> None:
    """Test if response is instance of frame class."""

    for response in (
        ProgramVersionResponse,
        DeviceAvailableResponse,
        UIDResponse,
        PasswordResponse,
        EcomaxParametersResponse,
        MixerParametersResponse,
        DataSchemaResponse,
        AlertsResponse,
    ):
        frame = response(recipient=DeviceTypes.ALL, sender=DeviceTypes.ECONET)
        assert isinstance(frame, response)


def test_program_version_response(
    data: Dict[int, DeviceDataType], messages: Dict[int, bytearray]
) -> None:
    """Test creating program version message."""
    frame1 = ProgramVersionResponse(data=data[FrameTypes.RESPONSE_PROGRAM_VERSION])
    frame2 = ProgramVersionResponse(
        message=messages[FrameTypes.RESPONSE_PROGRAM_VERSION]
    )
    assert frame1.message == messages[FrameTypes.RESPONSE_PROGRAM_VERSION]
    assert frame2.data == data[FrameTypes.RESPONSE_PROGRAM_VERSION]


def test_device_available_response(
    data: Dict[int, DeviceDataType],
    messages: Dict[int, bytearray],
) -> None:
    """Test creating device available message."""
    frame1 = DeviceAvailableResponse(data=data[FrameTypes.RESPONSE_DEVICE_AVAILABLE])
    frame2 = DeviceAvailableResponse(
        message=messages[FrameTypes.RESPONSE_DEVICE_AVAILABLE]
    )
    assert frame1.message == messages[FrameTypes.RESPONSE_DEVICE_AVAILABLE]
    assert frame2.data == data[FrameTypes.RESPONSE_DEVICE_AVAILABLE]


def test_uid_response(
    data: Dict[int, DeviceDataType],
    messages: Dict[int, bytearray],
) -> None:
    """Test parsing UID message."""
    frame1 = UIDResponse(message=messages[FrameTypes.RESPONSE_UID])
    frame2 = UIDResponse(data=data[FrameTypes.RESPONSE_UID])
    assert frame1.data == data[FrameTypes.RESPONSE_UID]
    assert not frame2.message


def test_password_response(
    data: Dict[int, DeviceDataType],
    messages: Dict[int, bytearray],
) -> None:
    """Test parsing password message."""
    frame1 = PasswordResponse(message=messages[FrameTypes.RESPONSE_PASSWORD])
    frame2 = PasswordResponse(data=data[FrameTypes.RESPONSE_PASSWORD])
    assert frame1.data == data[FrameTypes.RESPONSE_PASSWORD]
    assert not frame2.message


def test_ecomax_parameters_response(
    data: Dict[int, DeviceDataType],
    messages: Dict[int, bytearray],
) -> None:
    """Test parsing ecoMAX parameters message."""
    frame1 = EcomaxParametersResponse(
        message=messages[FrameTypes.RESPONSE_ECOMAX_PARAMETERS]
    )
    frame2 = EcomaxParametersResponse(data=data[FrameTypes.RESPONSE_ECOMAX_PARAMETERS])
    assert frame1.data == data[FrameTypes.RESPONSE_ECOMAX_PARAMETERS]
    assert not frame2.message


def test_mixer_parameters_response(
    data: Dict[int, DeviceDataType],
    messages: Dict[int, bytearray],
) -> None:
    """Test parsing message for mixer parameters response."""
    frame1 = MixerParametersResponse(
        message=messages[FrameTypes.RESPONSE_MIXER_PARAMETERS]
    )
    frame2 = MixerParametersResponse(data=data[FrameTypes.RESPONSE_MIXER_PARAMETERS])
    assert frame1.data == data[FrameTypes.RESPONSE_MIXER_PARAMETERS]
    assert not frame2.message

    # Test with empty parameters.
    frame1 = MixerParametersResponse(message=bytearray.fromhex("00000201"))
    assert frame1.data is None


def test_data_schema_response(messages: Dict[int, bytearray]) -> None:
    """Test parsing message for data schema response."""
    frame = DataSchemaResponse(message=messages[FrameTypes.RESPONSE_DATA_SCHEMA])
    assert ATTR_SCHEMA in frame.data
    assert len(frame.data[ATTR_SCHEMA]) == 257
    matches = {
        x[0]: x[1] for x in frame.data[ATTR_SCHEMA] if x[0] in REGDATA_SCHEMA.values()
    }
    assert list(matches.keys()).sort() == list(REGDATA_SCHEMA.values()).sort()
    assert isinstance(matches[ATTR_STATE], Byte)


def test_data_schema_response_with_no_parameters() -> None:
    """Test parsing message for data schema with no parameters."""
    frame = DataSchemaResponse(message=bytearray.fromhex("0000"))
    assert frame.data == {ATTR_SCHEMA: []}


def test_alerts_response(
    data: Dict[int, DeviceDataType],
    messages: Dict[int, bytearray],
) -> None:
    """Test alert response."""
    frame1 = AlertsResponse(message=messages[FrameTypes.RESPONSE_ALERTS])
    frame2 = AlertsResponse(data=data[FrameTypes.RESPONSE_ALERTS])
    assert frame1.data == data[FrameTypes.RESPONSE_ALERTS]
    assert not frame2.message


def test_schedule_response(
    data: Dict[int, DeviceDataType], messages: Dict[int, bytearray]
) -> None:
    """Test schedule response."""
    frame1 = SchedulesResponse(message=messages[FrameTypes.RESPONSE_SCHEDULES])
    frame2 = SchedulesResponse(data=data[FrameTypes.RESPONSE_SCHEDULES])
    assert frame1.data == data[FrameTypes.RESPONSE_SCHEDULES]
    assert not frame2.message
