"""Test PyPlumIO message frames."""

from typing import Dict

from pyplumio.const import (
    ATTR_ECOMAX_SENSORS,
    ATTR_FRAME_VERSIONS,
    ATTR_FUEL_LEVEL,
    ATTR_LAMBDA_SENSOR,
    ATTR_MIXER_SENSORS,
    ATTR_MODE,
    ATTR_MODULES,
    ATTR_PENDING_ALERTS,
    ATTR_THERMOSTATS,
    AddressTypes,
    FrameTypes,
)
from pyplumio.frames.messages import RegulatorDataMessage, SensorDataMessage


def test_messages_type() -> None:
    """Test if response is instance of frame class."""
    for response in (
        RegulatorDataMessage,
        SensorDataMessage,
    ):
        frame = response(recipient=AddressTypes.BROADCAST, sender=AddressTypes.ECONET)
        assert isinstance(frame, response)


def test_regdata_decode_message(messages: Dict[int, bytearray]) -> None:
    """Test parsing of regdata message."""
    frame = RegulatorDataMessage(message=messages[FrameTypes.MESSAGE_REGULATOR_DATA])
    assert ATTR_FRAME_VERSIONS in frame.data


def test_regdata_decode_message_with_unknown_version() -> None:
    """Test parsing of regdata message with unknown message version."""
    frame = RegulatorDataMessage()
    frame.decode_message(message=bytearray.fromhex("62640002"))
    assert not frame.data


def test_current_data_decode_message(messages: Dict[int, bytearray]) -> None:
    """Test parsing current data message."""
    frame = SensorDataMessage(message=messages[FrameTypes.MESSAGE_SENSOR_DATA])
    data = frame.data[ATTR_ECOMAX_SENSORS]
    assert ATTR_FRAME_VERSIONS in data
    assert data[ATTR_FRAME_VERSIONS][85] == 45559
    assert len(data[ATTR_FRAME_VERSIONS]) == 7
    assert data[ATTR_MODE] == 0
    assert round(data["heating_temp"], 2) == 22.38
    assert data["heating_target"] == 41
    assert not data["heating_pump"]
    assert data["heating_status"] == 0
    assert data[ATTR_MODULES].module_a == "18.11.58.K1"
    assert data[ATTR_MODULES].module_panel == "18.10.72"
    assert data[ATTR_LAMBDA_SENSOR]["lambda_level"] == 40
    assert ATTR_MIXER_SENSORS in data
    assert len(data[ATTR_MIXER_SENSORS]) == 1
    assert data[ATTR_MIXER_SENSORS][0]["mixer_temp"] == 20.0
    assert data[ATTR_MIXER_SENSORS][0]["mixer_target"] == 40
    assert data[ATTR_PENDING_ALERTS] == []
    assert data[ATTR_FUEL_LEVEL] == 32
    assert data[ATTR_THERMOSTATS][0]["contacts"]
    assert not data[ATTR_THERMOSTATS][0]["schedule"]
    assert data[ATTR_THERMOSTATS][0]["target"] == 50


def test_current_data_without_thermostats(
    sensor_data_without_thermostats: bytearray,
) -> None:
    """Test that thermostats key is not present in the device data
    if thermostats data is not present in the frame message.
    """
    frame = SensorDataMessage(message=sensor_data_without_thermostats)
    assert ATTR_THERMOSTATS not in frame.data
