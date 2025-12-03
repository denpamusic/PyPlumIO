"""Contains a tests for the request frame classes."""

import pytest
from tests.conftest import load_json_parameters

from pyplumio.const import DeviceType
from pyplumio.exceptions import FrameDataError
from pyplumio.frames import Request, Response, requests, responses
from pyplumio.structures.network_info import (
    ATTR_NETWORK_INFO,
    EthernetParameters,
    NetworkInfo,
)


def test_request_class_response_property() -> None:
    """Test response property for base request class."""
    assert Request().create_response() is None


def test_request_class_validate_response() -> None:
    """Test validate_response() for base request class."""
    with pytest.raises(NotImplementedError):
        Request().validate_response(Response())


def test_program_version_response_recipient_and_type() -> None:
    """Test if program version response recipient and type is set."""
    frame = requests.ProgramVersionRequest(
        recipient=DeviceType.ALL, sender=DeviceType.ECONET
    )
    response = frame.create_response()
    assert isinstance(response, responses.ProgramVersionResponse)
    assert response.recipient == DeviceType.ECONET


def test_check_device_response_recipient_and_type() -> None:
    """Test if check device response recipient and type is set."""
    frame = requests.CheckDeviceRequest(
        recipient=DeviceType.ALL, sender=DeviceType.ECONET
    )
    network_info = NetworkInfo(ethernet=EthernetParameters(ip="192.168.1.1"))
    response = frame.create_response(network_info=network_info)
    assert isinstance(response, responses.DeviceAvailableResponse)
    assert response.recipient == DeviceType.ECONET
    assert response.data[ATTR_NETWORK_INFO] is network_info


def test_check_device_validate_response() -> None:
    """Test response validation."""
    request = requests.CheckDeviceRequest(
        recipient=DeviceType.ALL, sender=DeviceType.ECONET
    )
    assert request.validate_response(responses.DeviceAvailableResponse()) is True
    assert request.validate_response(responses.AlertsResponse()) is False


@pytest.mark.parametrize(
    ("message", "data"),
    load_json_parameters("requests/ecomax_control.json"),
)
def test_ecomax_control(message, data) -> None:
    """Test an ecoMAX control parameter request."""
    assert requests.EcomaxControlRequest(data=data).message == message


def test_ecomax_control_without_data() -> None:
    """Test an ecoMAX control request without any data."""
    with pytest.raises(FrameDataError):
        getattr(requests.EcomaxControlRequest(), "message")


@pytest.mark.parametrize(
    ("message", "data"),
    load_json_parameters("requests/ecomax_parameters.json"),
)
def test_ecomax_parameters(message, data) -> None:
    """Test an ecoMAX parameters request."""
    request = requests.EcomaxParametersRequest(data=data)
    assert request.message == message
    assert request.response is responses.EcomaxParametersResponse


@pytest.mark.parametrize(
    ("message", "data"),
    load_json_parameters("requests/set_ecomax_parameter.json"),
)
def test_set_ecomax_parameter(message, data) -> None:
    """Test a set ecoMAX parameter request."""
    request = requests.SetEcomaxParameterRequest(data=data)
    assert request.message == message
    assert request.response is responses.SetEcomaxParameterResponse


def test_set_ecomax_parameter_without_data() -> None:
    """Test a set ecoMAX parameter request without any data."""
    with pytest.raises(FrameDataError):
        getattr(requests.SetEcomaxParameterRequest(), "message")


@pytest.mark.parametrize(
    ("message", "data"),
    load_json_parameters("requests/mixer_parameters.json"),
)
def test_mixer_parameters_request(message, data) -> None:
    """Test a mixer parameters request."""
    request = requests.MixerParametersRequest(data=data)
    assert request.message == message
    assert request.response is responses.MixerParametersResponse


@pytest.mark.parametrize(
    ("message", "data"),
    load_json_parameters("requests/set_mixer_parameter.json"),
)
def test_set_mixer_parameter(message, data) -> None:
    """Test a set mixer parameter request."""
    request = requests.SetMixerParameterRequest(data=data)
    assert request.message == message
    assert request.response is responses.SetMixerParameterResponse


def test_set_mixer_parameter_without_data() -> None:
    """Test a set mixer parameter request without any data."""
    with pytest.raises(FrameDataError):
        getattr(requests.SetMixerParameterRequest(), "message")


@pytest.mark.parametrize(
    ("message", "data"),
    load_json_parameters("requests/set_schedule.json"),
)
def test_set_schedule(message, data) -> None:
    """Test a set schedule request bytes."""
    request = requests.SetScheduleRequest(data=data)
    assert request.message == message
    assert not hasattr(request, "response")


def test_set_schedule_without_data() -> None:
    """Test a set schedule request without any data."""
    with pytest.raises(FrameDataError):
        getattr(requests.SetScheduleRequest(), "message")


@pytest.mark.parametrize(
    ("message", "data"),
    load_json_parameters("requests/thermostat_parameters.json"),
)
def test_thermostat_parameters_request(message, data) -> None:
    """Test a thermostat parameters request."""
    request = requests.ThermostatParametersRequest(data=data)
    assert request.message == message
    assert request.response is responses.ThermostatParametersResponse


@pytest.mark.parametrize(
    ("message", "data"),
    load_json_parameters("requests/set_thermostat_parameter.json"),
)
def test_set_thermostat_parameter(message, data) -> None:
    """Test a set thermostat parameter request."""
    request = requests.SetThermostatParameterRequest(data=data)
    assert request.message == message
    assert request.response is responses.SetThermostatParameterResponse


def test_set_thermostat_parameter_without_data() -> None:
    """Test a set thermostat parameter request without any data."""
    with pytest.raises(FrameDataError):
        getattr(requests.SetThermostatParameterRequest(), "message")


@pytest.mark.parametrize(
    ("message", "data"),
    load_json_parameters("requests/alerts.json"),
)
def test_alerts_request(message, data) -> None:
    """Test an alerts request."""
    request = requests.AlertsRequest(data=data)
    assert request.message == message
    assert request.response is responses.AlertsResponse
