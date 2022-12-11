"""Test PyPlumIO request frames."""

from typing import Dict

import pytest

from pyplumio.const import AddressTypes, FrameTypes
from pyplumio.exceptions import FrameDataError
from pyplumio.frames import Request
from pyplumio.frames.requests import (
    AlertsRequest,
    CheckDeviceRequest,
    DataSchemaRequest,
    EcomaxControlRequest,
    EcomaxParametersRequest,
    MixerParametersRequest,
    PasswordRequest,
    ProgramVersionRequest,
    SetEcomaxParameterRequest,
    SetMixerParameterRequest,
    SetScheduleRequest,
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
        EcomaxParametersRequest,
        MixerParametersRequest,
        DataSchemaRequest,
        StartMasterRequest,
        StopMasterRequest,
        AlertsRequest,
    ):
        frame = request(recipient=AddressTypes.BROADCAST, sender=AddressTypes.ECONET)
        assert isinstance(frame, request)


def test_program_version_response_recipient_and_type() -> None:
    """Test if program version response recipient and type is set."""
    frame = ProgramVersionRequest(
        recipient=AddressTypes.BROADCAST, sender=AddressTypes.ECONET
    )
    assert isinstance(frame.response(), ProgramVersionResponse)
    assert frame.response().recipient == AddressTypes.ECONET


def test_check_device_response_recipient_and_type() -> None:
    """Test if check device response recipient and type is set."""
    frame = CheckDeviceRequest(
        recipient=AddressTypes.BROADCAST, sender=AddressTypes.ECONET
    )
    assert isinstance(frame.response(), DeviceAvailableResponse)
    assert frame.response().recipient == AddressTypes.ECONET


def test_parameters(messages: Dict[int, bytearray]) -> None:
    """Test parameters request bytes."""
    frame = EcomaxParametersRequest()
    assert frame.message == messages[FrameTypes.REQUEST_ECOMAX_PARAMETERS]


def test_set_parameter(
    data: Dict[int, DeviceDataType], messages: Dict[int, bytearray]
) -> None:
    """Test set parameter request bytes."""
    frame = SetEcomaxParameterRequest(
        data=data[FrameTypes.REQUEST_SET_ECOMAX_PARAMETER]
    )
    assert frame.message == messages[FrameTypes.REQUEST_SET_ECOMAX_PARAMETER]


def test_set_parameter_with_no_data() -> None:
    """Test set parameter request with no data."""
    with pytest.raises(FrameDataError):
        SetEcomaxParameterRequest()


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


def test_ecomax_control(
    data: Dict[int, DeviceDataType], messages: Dict[int, bytearray]
) -> None:
    """Test ecoMAX control parameter request bytes."""
    frame = EcomaxControlRequest(data=data[FrameTypes.REQUEST_ECOMAX_CONTROL])
    assert frame.message == messages[FrameTypes.REQUEST_ECOMAX_CONTROL]


def test_ecomax_control_with_no_data() -> None:
    """Test ecoMAX control request with no data."""
    with pytest.raises(FrameDataError):
        EcomaxControlRequest()


def test_set_schedule(
    data: Dict[int, DeviceDataType], messages: Dict[int, bytearray]
) -> None:
    """Test set schedule request bytes."""
    frame = SetScheduleRequest(data=data[FrameTypes.REQUEST_SET_SCHEDULE])
    assert frame.message == messages[FrameTypes.REQUEST_SET_SCHEDULE]


def test_set_schedule_with_no_data() -> None:
    """Test set schedule request with no data."""
    with pytest.raises(FrameDataError):
        SetScheduleRequest()
