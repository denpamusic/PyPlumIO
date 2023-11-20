"""Contains tests for the response frame classes."""

import pytest

from pyplumio.const import DeviceType
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.frames.responses import (
    AlertsResponse,
    DeviceAvailableResponse,
    EcomaxParametersResponse,
    MixerParametersResponse,
    PasswordResponse,
    ProgramVersionResponse,
    RegulatorDataSchemaResponse,
    SchedulesResponse,
    ThermostatParametersResponse,
    UIDResponse,
)
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
        RegulatorDataSchemaResponse,
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
    load_json_parameters("responses/regulator_data_schema.json"),
)
def test_regulator_data_schema_response(message, data) -> None:
    """Test a regulator data schema response."""
    assert RegulatorDataSchemaResponse(message=message).data == data
    assert not RegulatorDataSchemaResponse(data=data).message


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
async def test_thermostat_parameters_response(ecomax: EcoMAX, message, data) -> None:
    """Test a thermostat parameters response."""
    frame = ThermostatParametersResponse(message=message)
    frame.sender = ecomax
    frame.sender.load({ATTR_THERMOSTATS_CONNECTED: 3})
    await frame.sender.wait_until_done()

    assert frame.data == data


@pytest.mark.parametrize(
    "message, data",
    load_json_parameters("responses/uid.json"),
)
def test_uid_response(message, data) -> None:
    """Test an UID response."""
    assert UIDResponse(message=message).data == data
    assert not UIDResponse(data=data).message
