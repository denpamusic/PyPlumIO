"""Test PyPlumIO message frames."""

import pytest

from pyplumio.const import (
    ATTR_ALARMS,
    ATTR_BOILER_SENSORS,
    ATTR_FRAME_VERSIONS,
    ATTR_FUEL_LEVEL,
    ATTR_MIXER_SENSORS,
    ATTR_MODE,
    ATTR_MODULES,
    BROADCAST_ADDRESS,
    ECONET_ADDRESS,
)
from pyplumio.exceptions import VersionError
from pyplumio.frames import messages


def test_responses_type() -> None:
    """Test if response is instance of frame class."""
    for response in (
        messages.RegulatorData,
        messages.SensorData,
    ):
        frame = response(recipient=BROADCAST_ADDRESS, sender=ECONET_ADDRESS)
        assert isinstance(frame, response)


_regdata_bytes = bytearray.fromhex(
    """626400010855F7B15420BE6101003D183136010064010040041C5698FA0000000000FF0FFF0FFF0FF
F0FFF0FFF0F9F04080FFF0FFF0F0000000000000000000000000000000000000000000000000000C07F0000C
07F0000C07F0000C07F0000C07F0000C07FD012B341000000000000C07F0000C07F0000C07F0000C07F0000C
07F0000C07F0000C07F0000C07F0000C07F0000C07F0000C07F0000C07F0000C07F0000C07F2D28000000002
9000000002828000000002828000000800000000000000000000000000000000000000000003FFF7F0000000
0200000000000404000403F124B0100000000000000000000000202010000000000000000000000000000000
0000000000000150009001A000D000C001D00000000000000000000000000000000000000FFFFFF000000000
00000000000FFFFFF0000000000010164000000
""".replace(
        "\n", ""
    )
)
_regdata_bytes_unknown_version = bytearray.fromhex("62640002")


def test_regdata_parse_message() -> None:
    """Test parsing of regdata message."""
    frame = messages.RegulatorData(message=_regdata_bytes)
    assert ATTR_FRAME_VERSIONS in frame.data


def test_regdata_parse_message_with_unknown_version() -> None:
    """Test parsing of regdata message with unknown message version."""
    frame = messages.RegulatorData()
    with pytest.raises(VersionError, match=r".*version: 2\.0.*"):
        frame.parse_message(message=_regdata_bytes_unknown_version)


_current_data_bytes = bytearray.fromhex(
    """0755F7B15420BE5698FA3601003802003901003D18310000000000FF0300000900D012B34101FFFFF
FFF02FFFFFFFF03FFFFFFFF04FFFFFFFF05FFFFFFFF060000000007FFFFFFFF08FFFFFFFF29002D800020000
000000000000000000000000001120B3A4B01FFFFFFFF120A48FFFF05FFFFFFFF28000800FFFFFFFF2800080
0FFFFFFFF28000800FFFFFFFF28000800FFFFFFFF28000800
""".replace(
        "\n", ""
    )
)


def test_current_data_parse_message() -> None:
    """Test parsing current data message."""
    frame = messages.SensorData(message=_current_data_bytes)
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
    assert data[ATTR_ALARMS] == []
    assert data[ATTR_FUEL_LEVEL] == 32
