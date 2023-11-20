"""Contains a tests for the message frame classes."""


from typing import Final

import pytest

from pyplumio.const import ATTR_SENSORS, ATTR_STATE, DeviceType
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.frames.messages import RegulatorDataMessage, SensorDataMessage
from pyplumio.structures.frame_versions import ATTR_FRAME_VERSIONS
from pyplumio.structures.regulator_data import ATTR_REGDATA
from tests import load_json_parameters, load_json_test_data

INDEX_STATE: Final = 22


def test_messages_type() -> None:
    """Test if response is an instance of abstract frame class."""
    for response in (RegulatorDataMessage, SensorDataMessage):
        frame = response(recipient=DeviceType.ALL, sender=DeviceType.ECONET)
        assert isinstance(frame, response)


@pytest.mark.parametrize(
    "schema, regdata",
    zip(
        load_json_test_data("responses/regulator_data_schema.json"),
        load_json_test_data("messages/regulator_data.json"),
    ),
    ids=[
        "unknown_regulator_data_version",
        "EM350P2_regulator_data",
        "incomplete_boolean",
    ],
)
async def test_regulator_data_message(ecomax: EcoMAX, schema, regdata) -> None:
    """Test a regulator data message."""
    frame = RegulatorDataMessage(message=regdata["message"])
    frame.sender = ecomax
    frame.sender.load(schema["data"])
    await frame.sender.wait_until_done()

    if regdata["id"] == "unknown_regulator_data_version":
        assert ATTR_FRAME_VERSIONS not in frame.data
        assert ATTR_REGDATA not in frame.data
    else:
        print(frame.data)
        assert frame.data[ATTR_FRAME_VERSIONS] == regdata["data"][ATTR_FRAME_VERSIONS]
        assert frame.data[ATTR_REGDATA].data == regdata["data"][ATTR_REGDATA]


@pytest.mark.parametrize(
    "message, data",
    load_json_parameters("messages/sensor_data.json"),
)
def test_sensor_data_message(message, data) -> None:
    """Test a sensor data message."""
    assert SensorDataMessage(message=message).data == data


def test_sensor_data_message_with_unknown_state() -> None:
    """Test a sensor data message with an unknown device state."""
    test_data = load_json_test_data("messages/sensor_data.json")[0]
    message = test_data["message"]
    message[INDEX_STATE] = 99
    assert SensorDataMessage(message=message).data[ATTR_SENSORS][ATTR_STATE] == 99
