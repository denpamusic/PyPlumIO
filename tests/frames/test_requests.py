"""Contains a tests for the request frame classes."""

import pytest
from tests.conftest import load_json_parameters

from pyplumio.const import DeviceType
from pyplumio.exceptions import FrameDataError
from pyplumio.frames import Request
from pyplumio.frames.requests import (
    AlertsRequest,
    CheckDeviceRequest,
    EcomaxControlRequest,
    EcomaxParametersRequest,
    MixerParametersRequest,
    ProgramVersionRequest,
    SetEcomaxParameterRequest,
    SetMixerParameterRequest,
    SetScheduleRequest,
    SetThermostatParameterRequest,
    ThermostatParametersRequest,
)
from pyplumio.frames.responses import DeviceAvailableResponse, ProgramVersionResponse


def test_request_class_response_property() -> None:
    """Test response property for a abstract request class."""
    assert Request().response() is None


def test_program_version_response_recipient_and_type() -> None:
    """Test if program version response recipient and type is set."""
    frame = ProgramVersionRequest(recipient=DeviceType.ALL, sender=DeviceType.ECONET)
    response = frame.response()
    assert isinstance(response, ProgramVersionResponse)
    assert response.recipient == DeviceType.ECONET


def test_check_device_response_recipient_and_type() -> None:
    """Test if check device response recipient and type is set."""
    frame = CheckDeviceRequest(recipient=DeviceType.ALL, sender=DeviceType.ECONET)
    response = frame.response()
    assert isinstance(response, DeviceAvailableResponse)
    assert response.recipient == DeviceType.ECONET


@pytest.mark.parametrize(
    ("message", "data"),
    load_json_parameters("requests/ecomax_control.json"),
)
def test_ecomax_control(message, data) -> None:
    """Test an ecoMAX control parameter request."""
    assert EcomaxControlRequest(data=data).message == message


def test_ecomax_control_without_data() -> None:
    """Test an ecoMAX control request without any data."""
    with pytest.raises(FrameDataError):
        getattr(EcomaxControlRequest(), "message")


@pytest.mark.parametrize(
    ("message", "data"),
    load_json_parameters("requests/ecomax_parameters.json"),
)
def test_ecomax_parameters(message, data) -> None:
    """Test an ecoMAX parameters request."""
    assert EcomaxParametersRequest(data=data).message == message


@pytest.mark.parametrize(
    ("message", "data"),
    load_json_parameters("requests/set_ecomax_parameter.json"),
)
def test_set_ecomax_parameter(message, data) -> None:
    """Test a set ecoMAX parameter request."""
    assert SetEcomaxParameterRequest(data=data).message == message


def test_set_ecomax_parameter_without_data() -> None:
    """Test a set ecoMAX parameter request without any data."""
    with pytest.raises(FrameDataError):
        getattr(SetEcomaxParameterRequest(), "message")


@pytest.mark.parametrize(
    ("message", "data"),
    load_json_parameters("requests/mixer_parameters.json"),
)
def test_mixer_parameters_request(message, data) -> None:
    """Test a mixer parameters request."""
    assert MixerParametersRequest(data=data).message == message


@pytest.mark.parametrize(
    ("message", "data"),
    load_json_parameters("requests/set_mixer_parameter.json"),
)
def test_set_mixer_parameter(message, data) -> None:
    """Test a set mixer parameter request."""
    assert SetMixerParameterRequest(data=data).message == message


def test_set_mixer_parameter_without_data() -> None:
    """Test a set mixer parameter request without any data."""
    with pytest.raises(FrameDataError):
        getattr(SetMixerParameterRequest(), "message")


@pytest.mark.parametrize(
    ("message", "data"),
    load_json_parameters("requests/set_schedule.json"),
)
def test_set_schedule(message, data) -> None:
    """Test a set schedule request bytes."""
    assert SetScheduleRequest(data=data).message == message


def test_set_schedule_without_data() -> None:
    """Test a set schedule request without any data."""
    with pytest.raises(FrameDataError):
        getattr(SetScheduleRequest(), "message")


@pytest.mark.parametrize(
    ("message", "data"),
    load_json_parameters("requests/thermostat_parameters.json"),
)
def test_thermostat_parameters_request(message, data) -> None:
    """Test a thermostat parameters request."""
    assert ThermostatParametersRequest(data=data).message == message


@pytest.mark.parametrize(
    ("message", "data"),
    load_json_parameters("requests/set_thermostat_parameter.json"),
)
def test_set_thermostat_parameter(message, data) -> None:
    """Test a set thermostat parameter request."""
    assert SetThermostatParameterRequest(data=data).message == message


def test_set_thermostat_parameter_without_data() -> None:
    """Test a set thermostat parameter request without any data."""
    with pytest.raises(FrameDataError):
        getattr(SetThermostatParameterRequest(), "message")


@pytest.mark.parametrize(
    ("message", "data"),
    load_json_parameters("requests/alerts.json"),
)
def test_alerts_request(message, data) -> None:
    """Test an alerts request."""
    assert AlertsRequest(data=data).message == message
