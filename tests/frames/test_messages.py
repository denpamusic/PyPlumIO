"""Test PyPlumIO message frames."""

from typing import Dict

import pytest

from pyplumio.const import (
    ATTR_BOILER_SENSORS,
    ATTR_FRAME_VERSIONS,
    ATTR_FUEL_LEVEL,
    ATTR_MIXER_SENSORS,
    ATTR_MODE,
    ATTR_MODULES,
    ATTR_PENDING_ALERTS,
    BROADCAST_ADDRESS,
    ECONET_ADDRESS,
)
from pyplumio.exceptions import VersionError
from pyplumio.frames import MessageTypes
from pyplumio.frames.messages import RegulatorDataMessage, SensorDataMessage


def test_messages_type() -> None:
    """Test if response is instance of frame class."""
    for response in (
        RegulatorDataMessage,
        SensorDataMessage,
    ):
        frame = response(recipient=BROADCAST_ADDRESS, sender=ECONET_ADDRESS)
        assert isinstance(frame, response)


def test_regdata_decode_message(messages: Dict[int, bytearray]) -> None:
    """Test parsing of regdata message."""
    frame = RegulatorDataMessage(message=messages[MessageTypes.REGULATOR_DATA])
    assert ATTR_FRAME_VERSIONS in frame.data


def test_regdata_decode_message_with_unknown_version() -> None:
    """Test parsing of regdata message with unknown message version."""
    frame = RegulatorDataMessage()
    with pytest.raises(VersionError, match=r".*version 2\.0.*"):
        frame.decode_message(message=bytearray.fromhex("62640002"))


def test_current_data_decode_message(messages: Dict[int, bytearray]) -> None:
    """Test parsing current data message."""
    frame = SensorDataMessage(message=messages[MessageTypes.SENSOR_DATA])
    data = frame.data[ATTR_BOILER_SENSORS]
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
    assert ATTR_MIXER_SENSORS in data
    assert len(data[ATTR_MIXER_SENSORS]) == 5
    assert data[ATTR_MIXER_SENSORS][0]["target_temp"] == 40
    assert data[ATTR_PENDING_ALERTS] == []
    assert data[ATTR_FUEL_LEVEL] == 32
