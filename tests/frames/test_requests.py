"""Test PyPlumIO request frames."""

from typing import Dict

import pytest

from pyplumio.const import BROADCAST_ADDRESS, ECONET_ADDRESS
from pyplumio.exceptions import FrameDataError
from pyplumio.frames import FrameTypes, Request
from pyplumio.frames.requests import (
    AlertsRequest,
    BoilerControlRequest,
    BoilerParametersRequest,
    CheckDeviceRequest,
    DataSchemaRequest,
    MixerParametersRequest,
    PasswordRequest,
    ProgramVersionRequest,
    SetBoilerParameterRequest,
    SetMixerParameterRequest,
    StartMasterRequest,
    StopMasterRequest,
    UIDRequest,
)
from pyplumio.frames.responses import DeviceAvailableResponse, ProgramVersionResponse
from pyplumio.helpers.typing import DeviceDataType


def test_base_class_response() -> None:
    """Test response for base class."""
    assert Request().response() is None


def test_request_type() -> None:
    """Test if request is instance of frame class."""
    for request in (
        ProgramVersionRequest,
        CheckDeviceRequest,
        UIDRequest,
        PasswordRequest,
        BoilerParametersRequest,
        MixerParametersRequest,
        DataSchemaRequest,
        StartMasterRequest,
        StopMasterRequest,
        AlertsRequest,
    ):
        frame = request(recipient=BROADCAST_ADDRESS, sender=ECONET_ADDRESS)
        assert isinstance(frame, request)


def test_program_version_response_recipient_and_type() -> None:
    """Test if program version response recipient and type is set."""
    frame = ProgramVersionRequest(recipient=BROADCAST_ADDRESS, sender=ECONET_ADDRESS)
    assert isinstance(frame.response(), ProgramVersionResponse)
    assert frame.response().recipient == ECONET_ADDRESS


def test_check_device_response_recipient_and_type() -> None:
    """Test if check device response recipient and type is set."""
    frame = CheckDeviceRequest(recipient=BROADCAST_ADDRESS, sender=ECONET_ADDRESS)
    assert isinstance(frame.response(), DeviceAvailableResponse)
    assert frame.response().recipient == ECONET_ADDRESS


def test_parameters(messages: Dict[int, bytearray]) -> None:
    """Test parameters request bytes."""
    frame = BoilerParametersRequest()
    assert frame.message == messages[FrameTypes.REQUEST_BOILER_PARAMETERS]


def test_set_parameter(
    data: Dict[int, DeviceDataType], messages: Dict[int, bytearray]
) -> None:
    """Test set parameter request bytes."""
    frame = SetBoilerParameterRequest(
        data=data[FrameTypes.REQUEST_SET_BOILER_PARAMETER]
    )
    assert frame.message == messages[FrameTypes.REQUEST_SET_BOILER_PARAMETER]


def test_set_parameter_with_no_data() -> None:
    """Test set parameter request with no data."""
    with pytest.raises(FrameDataError):
        SetBoilerParameterRequest()


def test_set_mixer_parameter(
    data: Dict[int, DeviceDataType], messages: Dict[int, bytearray]
) -> None:
    """Test set mixer parameter request bytes."""
    frame = SetMixerParameterRequest(data=data[FrameTypes.REQUEST_SET_MIXER_PARAMETER])
    assert frame.message == messages[FrameTypes.REQUEST_SET_MIXER_PARAMETER]


def test_set_mixer_parameter_with_no_data() -> None:
    """Test set mixer parameter request with no data."""
    with pytest.raises(FrameDataError):
        SetMixerParameterRequest()


def test_boiler_control(
    data: Dict[int, DeviceDataType], messages: Dict[int, bytearray]
) -> None:
    """Test boiler control parameter request bytes."""
    frame = BoilerControlRequest(data=data[FrameTypes.REQUEST_BOILER_CONTROL])
    assert frame.message == messages[FrameTypes.REQUEST_BOILER_CONTROL]


def test_boiler_control_with_no_data() -> None:
    """Test boiler control request with no data."""
    with pytest.raises(FrameDataError):
        BoilerControlRequest()
