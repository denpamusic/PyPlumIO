"""Test PyPlumIO request frames."""

from pyplumio import requests, responses
from pyplumio.constants import BROADCAST_ADDRESS, ECONET_ADDRESS


def test_base_class_response() -> None:
    """Test response for base class."""
    assert requests.Request().response() is None


def test_request_type() -> None:
    """Test if request is instance of frame class."""
    for request in (
        requests.ProgramVersion,
        requests.CheckDevice,
        requests.UID,
        requests.Password,
        requests.BoilerParameters,
        requests.MixerParameters,
        requests.DataSchema,
        requests.StartMaster,
        requests.StopMaster,
    ):
        frame = request(recipient=BROADCAST_ADDRESS, sender=ECONET_ADDRESS)
        assert isinstance(frame, request)


def test_program_version_response_recipient_and_type() -> None:
    """Test if program version response recipient and type is set."""
    frame = requests.ProgramVersion(recipient=BROADCAST_ADDRESS, sender=ECONET_ADDRESS)
    assert isinstance(frame.response(), responses.ProgramVersion)
    assert frame.response().recipient == ECONET_ADDRESS


def test_check_device_response_recipient_and_type() -> None:
    """Test if check device response recipient and type is set."""
    frame = requests.CheckDevice(recipient=BROADCAST_ADDRESS, sender=ECONET_ADDRESS)
    assert isinstance(frame.response(), responses.DeviceAvailable)
    assert frame.response().recipient == ECONET_ADDRESS


def test_parameters() -> None:
    """Test parameters request bytes."""
    frame = requests.BoilerParameters()
    assert frame.bytes == b"\x68\x0c\x00\x00\x56\x30\x05\x31\xff\x00\xc9\x16"


def test_set_parameter() -> None:
    """Test set parameter request bytes."""
    frame = requests.SetParameter(data={"name": "airflow_power_100", "value": 80})
    assert frame.bytes == b"\x68\x0c\x00\x00\x56\x30\x05\x33\x00\x50\x64\x16"


def test_set_mixer_parameter() -> None:
    """Test set mixer parameter request bytes."""
    frame = requests.SetMixerParameter(
        data={"name": "mix_set_temp", "value": 40, "extra": 0}
    )
    assert frame.bytes == b"\x68\x0d\x00\x00\x56\x30\x05\x34\x00\x00\x28\x1a\x16"


def test_boiler_control() -> None:
    """Test boiler control parameter request bytes."""
    frame = requests.BoilerControl(data={"value": 1})
    assert frame.bytes == b"\x68\x0b\x00\x00\x56\x30\x05\x3b\x01\x3a\x16"
