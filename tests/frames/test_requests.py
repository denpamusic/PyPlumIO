"""Test PyPlumIO request frames."""

import pytest

from pyplumio.const import BROADCAST_ADDRESS, ECONET_ADDRESS
from pyplumio.exceptions import FrameDataError
from pyplumio.frames import Request
from pyplumio.frames.requests import (
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


def test_parameters() -> None:
    """Test parameters request bytes."""
    frame = BoilerParametersRequest()
    assert frame.bytes == b"\x68\x0c\x00\x00\x56\x30\x05\x31\xff\x00\xc9\x16"


def test_set_parameter() -> None:
    """Test set parameter request bytes."""
    frame = SetBoilerParameterRequest(data={"name": "airflow_power_100", "value": 80})
    assert frame.bytes == b"\x68\x0c\x00\x00\x56\x30\x05\x33\x00\x50\x64\x16"


def test_set_parameter_with_no_data() -> None:
    """Test set parameter request with no data."""
    with pytest.raises(FrameDataError):
        SetBoilerParameterRequest()


def test_set_mixer_parameter() -> None:
    """Test set mixer parameter request bytes."""
    frame = SetMixerParameterRequest(
        data={"name": "mix_target_temp", "value": 40, "extra": 0}
    )
    assert frame.bytes == b"\x68\x0d\x00\x00\x56\x30\x05\x34\x00\x00\x28\x1a\x16"


def test_set_mixer_parameter_with_no_data() -> None:
    """Test set mixer parameter request with no data."""
    with pytest.raises(FrameDataError):
        SetMixerParameterRequest()


def test_boiler_control() -> None:
    """Test boiler control parameter request bytes."""
    frame = BoilerControlRequest(data={"value": 1})
    assert frame.bytes == b"\x68\x0b\x00\x00\x56\x30\x05\x3b\x01\x3a\x16"


def test_boiler_control_with_no_data() -> None:
    """Test boiler control request with no data."""
    with pytest.raises(FrameDataError):
        BoilerControlRequest()
