"""Test PyPlumIO response frames."""

from pyplumio.const import DeviceType, FrameType
from pyplumio.frames.responses import (
    AlertsResponse,
    DataSchemaResponse,
    DeviceAvailableResponse,
    EcomaxParametersResponse,
    MixerParametersResponse,
    PasswordResponse,
    ProgramVersionResponse,
    SchedulesResponse,
    ThermostatParametersResponse,
    UIDResponse,
)
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures.data_schema import ATTR_SCHEMA
from pyplumio.structures.mixer_parameters import ATTR_MIXER_PARAMETERS
from pyplumio.structures.thermostat_parameters import (
    ATTR_THERMOSTAT_PARAMETERS,
    ATTR_THERMOSTAT_PARAMETERS_DECODER,
    ATTR_THERMOSTAT_PROFILE,
)
from pyplumio.structures.thermostat_sensors import ATTR_THERMOSTAT_COUNT


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
        frame = response(recipient=DeviceType.ALL, sender=DeviceType.ECONET)
        assert isinstance(frame, response)


def test_program_version_response(
    data: dict[int, DeviceDataType], messages: dict[int, bytearray]
) -> None:
    """Test creating program version message."""
    frame1 = ProgramVersionResponse(data=data[FrameType.RESPONSE_PROGRAM_VERSION])
    frame2 = ProgramVersionResponse(
        message=messages[FrameType.RESPONSE_PROGRAM_VERSION]
    )
    assert frame1.message == messages[FrameType.RESPONSE_PROGRAM_VERSION]
    assert frame2.data == data[FrameType.RESPONSE_PROGRAM_VERSION]


def test_device_available_response(
    data: dict[int, DeviceDataType],
    messages: dict[int, bytearray],
) -> None:
    """Test creating device available message."""
    frame1 = DeviceAvailableResponse(data=data[FrameType.RESPONSE_DEVICE_AVAILABLE])
    frame2 = DeviceAvailableResponse(
        message=messages[FrameType.RESPONSE_DEVICE_AVAILABLE]
    )
    assert frame1.message == messages[FrameType.RESPONSE_DEVICE_AVAILABLE]
    assert frame2.data == data[FrameType.RESPONSE_DEVICE_AVAILABLE]


def test_uid_response(
    data: dict[int, DeviceDataType],
    messages: dict[int, bytearray],
) -> None:
    """Test parsing UID message."""
    frame1 = UIDResponse(message=messages[FrameType.RESPONSE_UID])
    frame2 = UIDResponse(data=data[FrameType.RESPONSE_UID])
    assert frame1.data == data[FrameType.RESPONSE_UID]
    assert not frame2.message


def test_password_response(
    data: dict[int, DeviceDataType],
    messages: dict[int, bytearray],
) -> None:
    """Test parsing password message."""
    frame1 = PasswordResponse(message=messages[FrameType.RESPONSE_PASSWORD])
    frame2 = PasswordResponse(data=data[FrameType.RESPONSE_PASSWORD])
    assert frame1.data == data[FrameType.RESPONSE_PASSWORD]
    assert not frame2.message


def test_ecomax_parameters_response(
    data: dict[int, DeviceDataType],
    messages: dict[int, bytearray],
) -> None:
    """Test parsing ecoMAX parameters message."""
    frame1 = EcomaxParametersResponse(
        message=messages[FrameType.RESPONSE_ECOMAX_PARAMETERS]
    )
    frame2 = EcomaxParametersResponse(data=data[FrameType.RESPONSE_ECOMAX_PARAMETERS])
    assert frame1.data == data[FrameType.RESPONSE_ECOMAX_PARAMETERS]
    assert not frame2.message


def test_mixer_parameters_response(
    data: dict[int, DeviceDataType],
    messages: dict[int, bytearray],
) -> None:
    """Test parsing message for mixer parameters response."""
    frame1 = MixerParametersResponse(
        message=messages[FrameType.RESPONSE_MIXER_PARAMETERS]
    )
    frame2 = MixerParametersResponse(data=data[FrameType.RESPONSE_MIXER_PARAMETERS])
    assert frame1.data == data[FrameType.RESPONSE_MIXER_PARAMETERS]
    assert not frame2.message

    # Test with empty parameters.
    frame1 = MixerParametersResponse(message=bytearray.fromhex("00000201"))
    assert frame1.data == {ATTR_MIXER_PARAMETERS: None}


def test_thermostat_parameters_response(
    data: dict[int, DeviceDataType],
    messages: dict[int, bytearray],
) -> None:
    """Test parsing message for thermostat parameters response."""
    frame = ThermostatParametersResponse(
        message=messages[FrameType.RESPONSE_THERMOSTAT_PARAMETERS]
    )
    decoder = frame.data[ATTR_THERMOSTAT_PARAMETERS_DECODER]
    frame_data = decoder.decode(
        message=frame.message,
        data={ATTR_THERMOSTAT_COUNT: 3},
    )[0]
    assert frame_data == data[FrameType.RESPONSE_THERMOSTAT_PARAMETERS]


def test_thermostat_parameters_response_with_no_parameters() -> None:
    """Test parsing message for the thermosat parameters response
    with no parameters."""
    frame = ThermostatParametersResponse(
        message=bytearray.fromhex("00000300FFFFFFFFFFFFFFFFFF")
    )
    decoder = frame.data[ATTR_THERMOSTAT_PARAMETERS_DECODER]
    frame_data = decoder.decode(
        message=frame.message,
        data={ATTR_THERMOSTAT_COUNT: 2},
    )[0]
    assert frame_data == {
        ATTR_THERMOSTAT_COUNT: 2,
        ATTR_THERMOSTAT_PROFILE: None,
        ATTR_THERMOSTAT_PARAMETERS: None,
    }


def test_data_schema_response(messages: dict[int, bytearray]) -> None:
    """Test parsing message for data schema response."""
    frame = DataSchemaResponse(message=messages[FrameType.RESPONSE_DATA_SCHEMA])
    assert ATTR_SCHEMA in frame.data
    assert len(frame.data[ATTR_SCHEMA]) == 257


def test_data_schema_response_with_no_parameters() -> None:
    """Test parsing message for data schema with no parameters."""
    frame = DataSchemaResponse(message=bytearray.fromhex("0000"))
    assert ATTR_SCHEMA not in frame.data


def test_alerts_response(
    data: dict[int, DeviceDataType],
    messages: dict[int, bytearray],
) -> None:
    """Test alert response."""
    frame1 = AlertsResponse(message=messages[FrameType.RESPONSE_ALERTS])
    frame2 = AlertsResponse(data=data[FrameType.RESPONSE_ALERTS])
    assert frame1.data == data[FrameType.RESPONSE_ALERTS]
    assert not frame2.message


def test_schedule_response(
    data: dict[int, DeviceDataType], messages: dict[int, bytearray]
) -> None:
    """Test schedule response."""
    frame1 = SchedulesResponse(message=messages[FrameType.RESPONSE_SCHEDULES])
    frame2 = SchedulesResponse(data=data[FrameType.RESPONSE_SCHEDULES])
    assert frame1.data == data[FrameType.RESPONSE_SCHEDULES]
    assert not frame2.message
