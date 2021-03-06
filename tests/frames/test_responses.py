"""Test PyPlumIO response frames."""

from typing import Dict

from pyplumio.const import ATTR_MODE, ATTR_SCHEMA, BROADCAST_ADDRESS, ECONET_ADDRESS
from pyplumio.frames import ResponseTypes
from pyplumio.frames.responses import (
    AlertsResponse,
    BoilerParametersResponse,
    DataSchemaResponse,
    DeviceAvailableResponse,
    MixerParametersResponse,
    PasswordResponse,
    ProgramVersionResponse,
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
        BoilerParametersResponse,
        MixerParametersResponse,
        DataSchemaResponse,
        AlertsResponse,
    ):
        frame = response(recipient=BROADCAST_ADDRESS, sender=ECONET_ADDRESS)
        assert isinstance(frame, response)


def test_program_version_response(
    data: Dict[int, DeviceDataType], messages: Dict[int, bytearray]
) -> None:
    """Test creating program version message."""
    frame1 = ProgramVersionResponse(data=data[ResponseTypes.PROGRAM_VERSION])
    frame2 = ProgramVersionResponse(message=messages[ResponseTypes.PROGRAM_VERSION])
    assert frame1.message == messages[ResponseTypes.PROGRAM_VERSION]
    assert frame2.data == data[ResponseTypes.PROGRAM_VERSION]


def test_device_available_response(
    data: Dict[int, DeviceDataType],
    messages: Dict[int, bytearray],
) -> None:
    """Test creating device available message."""
    frame1 = DeviceAvailableResponse(data=data[ResponseTypes.DEVICE_AVAILABLE])
    frame2 = DeviceAvailableResponse(message=messages[ResponseTypes.DEVICE_AVAILABLE])
    assert frame1.message == messages[ResponseTypes.DEVICE_AVAILABLE]
    assert frame2.data == data[ResponseTypes.DEVICE_AVAILABLE]


def test_uid_response(
    data: Dict[int, DeviceDataType],
    messages: Dict[int, bytearray],
) -> None:
    """Test parsing UID message."""
    frame1 = UIDResponse(message=messages[ResponseTypes.UID])
    frame2 = UIDResponse(data=data[ResponseTypes.UID])
    assert frame1.data == data[ResponseTypes.UID]
    assert not frame2.message


def test_password_response(
    data: Dict[int, DeviceDataType],
    messages: Dict[int, bytearray],
) -> None:
    """Test parsing password message."""
    frame1 = PasswordResponse(message=messages[ResponseTypes.PASSWORD])
    frame2 = PasswordResponse(data=data[ResponseTypes.PASSWORD])
    assert frame1.data == data[ResponseTypes.PASSWORD]
    assert not frame2.message


def test_boiler_parameters_response(
    data: Dict[int, DeviceDataType],
    messages: Dict[int, bytearray],
) -> None:
    """Test parsing boiler parameters message."""
    frame1 = BoilerParametersResponse(message=messages[ResponseTypes.BOILER_PARAMETERS])
    frame2 = BoilerParametersResponse(data=data[ResponseTypes.BOILER_PARAMETERS])
    assert frame1.data == data[ResponseTypes.BOILER_PARAMETERS]
    assert not frame2.message


def test_mixer_parameters_response(
    data: Dict[int, DeviceDataType],
    messages: Dict[int, bytearray],
) -> None:
    """Test parsing message for mixer parameters response."""
    frame1 = MixerParametersResponse(message=messages[ResponseTypes.MIXER_PARAMETERS])
    frame2 = MixerParametersResponse(data=data[ResponseTypes.MIXER_PARAMETERS])
    assert frame1.data == data[ResponseTypes.MIXER_PARAMETERS]
    assert not frame2.message


def test_data_schema_response(messages: Dict[int, bytearray]) -> None:
    """Test parsing message for data schema response."""
    frame = DataSchemaResponse(message=messages[ResponseTypes.DATA_SCHEMA])
    assert ATTR_SCHEMA in frame.data
    assert len(frame.data[ATTR_SCHEMA]) == 257
    matches = {
        x[0]: x[1] for x in frame.data[ATTR_SCHEMA] if x[0] in REGDATA_SCHEMA.values()
    }
    assert list(matches.keys()).sort() == list(REGDATA_SCHEMA.values()).sort()
    assert isinstance(matches[ATTR_MODE], Byte)


def test_data_schema_response_with_no_parameters() -> None:
    """Test parsing message for data schema with no parameters."""
    frame = DataSchemaResponse(message=bytearray.fromhex("0000"))
    assert frame.data == {ATTR_SCHEMA: []}


def test_alerts_response(
    data: Dict[int, DeviceDataType],
    messages: Dict[int, bytearray],
) -> None:
    """Test alert response."""
    frame1 = AlertsResponse(message=messages[ResponseTypes.ALERTS])
    frame2 = AlertsResponse(data=data[ResponseTypes.ALERTS])
    assert frame1.data == data[ResponseTypes.ALERTS]
    assert not frame2.message
