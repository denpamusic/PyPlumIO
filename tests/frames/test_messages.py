"""Contains a tests for the message frame classes."""

from typing import Final

import pytest
from tests.conftest import json_test_data, load_json_parameters, load_json_test_data

from pyplumio.const import ATTR_SENSORS, ATTR_STATE
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.frames.messages import RegulatorDataMessage, SensorDataMessage
from pyplumio.structures.frame_versions import ATTR_FRAME_VERSIONS
from pyplumio.structures.regulator_data import ATTR_REGDATA


@pytest.mark.parametrize(
    ("schema", "regdata"),
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
    frame.assign_to(ecomax)
    ecomax.load_nowait(schema["data"])
    await ecomax.wait_until_done()

    if regdata["id"] == "unknown_regulator_data_version":
        assert ATTR_FRAME_VERSIONS not in frame.data
        assert ATTR_REGDATA not in frame.data
    else:
        assert frame.data[ATTR_FRAME_VERSIONS] == regdata["data"][ATTR_FRAME_VERSIONS]
        assert frame.data[ATTR_REGDATA] == regdata["data"][ATTR_REGDATA]


@pytest.mark.parametrize(
    ("message", "data"),
    load_json_parameters("messages/sensor_data.json"),
)
def test_sensor_data_message(message, data) -> None:
    """Test a sensor data message."""
    assert SensorDataMessage(message=message).data == data


INDEX_STATE: Final = 22


@json_test_data("messages/sensor_data.json", selector="message")
async def test_sensor_data_message_with_unknown_state(sensor_data_message) -> None:
    """Test a sensor data message with an unknown device state."""
    sensor_data_message[INDEX_STATE] = 99
    sensor_data = SensorDataMessage(message=sensor_data_message)
    assert sensor_data.data[ATTR_SENSORS][ATTR_STATE] == 99
