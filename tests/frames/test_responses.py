"""Contains tests for the response frame classes."""

import pytest

from pyplumio.const import DeviceType
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
from pyplumio.structures.thermostat_parameters import ATTR_THERMOSTAT_PARAMETERS_DECODER
from pyplumio.structures.thermostat_sensors import ATTR_THERMOSTATS_CONNECTED
from tests import load_json_parameters


def test_responses_type() -> None:
    """Test if response is an instance of frame class."""

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


@pytest.mark.parametrize(
    "message, data",
    load_json_parameters("responses/alerts.json"),
)
def test_alerts_response(message, data) -> None:
    """Test an alerts response."""
    assert AlertsResponse(message=message).data == data
    assert not AlertsResponse(data=data).message


@pytest.mark.parametrize(
    "message, data",
    load_json_parameters("responses/data_schema.json"),
)
def test_data_schema_response(message, data) -> None:
    """Test a data schema response."""
    assert DataSchemaResponse(message=message).data == data
    assert not DataSchemaResponse(data=data).message


@pytest.mark.parametrize(
    "message, data",
    load_json_parameters("responses/device_available.json"),
)
def test_device_available_response(message, data) -> None:
    """Test a device available response."""
    assert DeviceAvailableResponse(data=data).message == message
    assert DeviceAvailableResponse(message=message).data == data


@pytest.mark.parametrize(
    "message, data",
    load_json_parameters("responses/ecomax_parameters.json"),
)
def test_ecomax_parameters_response(message, data) -> None:
    """Test a ecoMAX parameters response."""
    assert EcomaxParametersResponse(message=message).data == data
    assert not EcomaxParametersResponse(data=data).message


@pytest.mark.parametrize(
    "message, data",
    load_json_parameters("responses/mixer_parameters.json"),
)
def test_mixer_parameters_response(message, data) -> None:
    """Test a mixer parameters response."""
    assert MixerParametersResponse(message=message).data == data
    assert not MixerParametersResponse(data=data).message


@pytest.mark.parametrize(
    "message, data",
    load_json_parameters("responses/password.json"),
)
def test_password_response(message, data) -> None:
    """Test parsing password message."""
    assert PasswordResponse(message=message).data == data
    assert not PasswordResponse(data=data).message


@pytest.mark.parametrize(
    "message, data",
    load_json_parameters("responses/program_version.json"),
)
def test_program_version_response(message, data) -> None:
    """Test a program version response."""
    assert ProgramVersionResponse(data=data).message == message
    assert ProgramVersionResponse(message=message).data == data


@pytest.mark.parametrize(
    "message, data",
    load_json_parameters("responses/schedules.json"),
)
def test_schedules_response(message, data) -> None:
    """Test a schedules response."""
    assert SchedulesResponse(message=message).data == data
    assert not SchedulesResponse(data=data).message


@pytest.mark.parametrize(
    "message, data",
    load_json_parameters("responses/thermostat_parameters.json"),
)
def test_thermostat_parameters_response(message, data) -> None:
    """Test a thermostat parameters response."""
    frame = ThermostatParametersResponse(message=message)
    decoder = frame.data[ATTR_THERMOSTAT_PARAMETERS_DECODER]
    assert (
        decoder.decode(
            message=frame.message,
            data={ATTR_THERMOSTATS_CONNECTED: 3},
        )[0]
        == data
    )


@pytest.mark.parametrize(
    "message, data",
    load_json_parameters("responses/uid.json"),
)
def test_uid_response(message, data) -> None:
    """Test an UID response."""
    assert UIDResponse(message=message).data == data
    assert not UIDResponse(data=data).message
