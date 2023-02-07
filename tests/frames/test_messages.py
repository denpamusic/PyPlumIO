"""Test PyPlumIO message frames."""

from typing import Final

from pyplumio.const import (
    ATTR_CURRENT_TEMP,
    ATTR_SCHEDULE,
    ATTR_SENSORS,
    ATTR_STATE,
    ATTR_TARGET_TEMP,
    BYTE_UNDEFINED,
    DeviceState,
    DeviceType,
    FrameType,
)
from pyplumio.frames.messages import RegulatorDataMessage, SensorDataMessage
from pyplumio.structures.fan_power import ATTR_FAN_POWER
from pyplumio.structures.frame_versions import ATTR_FRAME_VERSIONS
from pyplumio.structures.fuel_consumption import ATTR_FUEL_CONSUMPTION
from pyplumio.structures.fuel_level import ATTR_FUEL_LEVEL
from pyplumio.structures.lambda_sensor import (
    ATTR_LAMBDA_LEVEL,
    ATTR_LAMBDA_STATE,
    ATTR_LAMBDA_TARGET,
)
from pyplumio.structures.load import ATTR_LOAD
from pyplumio.structures.mixer_sensors import ATTR_MIXER_SENSORS, ATTR_PUMP
from pyplumio.structures.modules import ATTR_MODULES
from pyplumio.structures.outputs import ATTR_HEATING_PUMP
from pyplumio.structures.pending_alerts import ATTR_PENDING_ALERTS
from pyplumio.structures.power import ATTR_POWER
from pyplumio.structures.regulator_data import ATTR_REGDATA_DECODER
from pyplumio.structures.statuses import ATTR_HEATING_STATUS, ATTR_HEATING_TARGET
from pyplumio.structures.temperatures import ATTR_HEATING_TEMP
from pyplumio.structures.thermostat_sensors import (
    ATTR_CONTACTS,
    ATTR_THERMOSTAT_SENSORS,
)

INDEX_VERSION_MINOR: Final = 3
INDEX_VERSION_MAJOR: Final = 4
INDEX_STATE: Final = 22
INDEX_FUEL_LEVEL: Final = 82
INDEX_FAN_POWER: Final = 84
INDEX_LOAD: Final = 88
INDEX_POWER: Final = 89
INDEX_FUEL_CONSUMPTION: Final = 93
INDEX_LAMBDA_SENSOR: Final = 110


def test_messages_type() -> None:
    """Test if response is instance of frame class."""
    for response in (
        RegulatorDataMessage,
        SensorDataMessage,
    ):
        frame = response(recipient=DeviceType.ALL, sender=DeviceType.ECONET)
        assert isinstance(frame, response)


def test_regdata_decode_message(messages: dict[FrameType, bytearray]) -> None:
    """Test parsing of regdata message."""
    frame = RegulatorDataMessage(message=messages[FrameType.MESSAGE_REGULATOR_DATA])
    decoder = frame.data[ATTR_REGDATA_DECODER]
    data = decoder.decode(frame.message)[0]
    assert ATTR_FRAME_VERSIONS in data


def test_regdata_decode_message_with_unknown_version(
    messages: dict[FrameType, bytearray]
) -> None:
    """Test parsing of regdata message with unknown message version."""
    test_message = messages[FrameType.MESSAGE_REGULATOR_DATA]
    test_message[INDEX_VERSION_MAJOR], test_message[INDEX_VERSION_MINOR] = (2, 0)
    frame = RegulatorDataMessage(message=test_message)
    decoder = frame.data[ATTR_REGDATA_DECODER]
    assert not decoder.decode(frame.message)[0]


def test_sensor_data_decode_message(messages: dict[FrameType, bytearray]) -> None:
    """Test parsing sensor data message."""
    test_message = messages[FrameType.MESSAGE_SENSOR_DATA]
    frame = SensorDataMessage(message=test_message)
    data = frame.data[ATTR_SENSORS]
    assert ATTR_FRAME_VERSIONS in data
    assert data[ATTR_FRAME_VERSIONS][85] == 45559
    assert len(data[ATTR_FRAME_VERSIONS]) == 7
    assert data[ATTR_STATE] == DeviceState.OFF
    assert round(data[ATTR_HEATING_TEMP], 2) == 22.38
    assert data[ATTR_HEATING_TARGET] == 41
    assert not data[ATTR_HEATING_PUMP]
    assert data[ATTR_HEATING_STATUS] == 0
    assert data[ATTR_MODULES].module_a == "18.11.58.K1"
    assert data[ATTR_MODULES].module_panel == "18.10.72"
    assert data[ATTR_LAMBDA_LEVEL] == 4.0
    assert data[ATTR_PENDING_ALERTS] == 0
    assert data[ATTR_FUEL_LEVEL] == 32
    assert data[ATTR_MIXER_SENSORS] == [
        (
            4,
            {
                ATTR_CURRENT_TEMP: 20.0,
                ATTR_TARGET_TEMP: 40,
                ATTR_PUMP: False,
            },
        )
    ]
    assert data[ATTR_THERMOSTAT_SENSORS] == [
        (
            0,
            {
                ATTR_STATE: 3,
                ATTR_CURRENT_TEMP: 43.5,
                ATTR_TARGET_TEMP: 50.0,
                ATTR_CONTACTS: True,
                ATTR_SCHEDULE: False,
            },
        )
    ]

    # Test with the unknown state.
    test_message[INDEX_STATE] = 12
    frame = SensorDataMessage(message=test_message)
    assert frame.data[ATTR_SENSORS][ATTR_STATE] == 12


def test_sensor_data_without_fuel_level_and_load(
    messages: dict[FrameType, bytearray]
) -> None:
    """Test that fuel level and load keys are not present in the device data
    if they are unavailable.
    """
    test_message = messages[FrameType.MESSAGE_SENSOR_DATA]
    for index in (INDEX_FUEL_LEVEL, INDEX_LOAD):
        test_message[index] = BYTE_UNDEFINED

    frame = SensorDataMessage(message=test_message)
    assert ATTR_FUEL_LEVEL not in frame.data
    assert ATTR_LOAD not in frame.data


def test_sensor_data_without_lambda_sensor(
    messages: dict[FrameType, bytearray]
) -> None:
    """Test that lambda sensor dict are not present in the device data
    if it is unavailable.
    """
    test_message = messages[FrameType.MESSAGE_SENSOR_DATA]
    test_message[INDEX_LAMBDA_SENSOR] = BYTE_UNDEFINED
    for byte in range(1, 6):
        del test_message[INDEX_LAMBDA_SENSOR + byte]

    frame = SensorDataMessage(message=test_message)
    assert ATTR_LAMBDA_STATE not in frame.data
    assert ATTR_LAMBDA_TARGET not in frame.data
    assert ATTR_LAMBDA_LEVEL not in frame.data


def test_sensor_data_without_fan_power_and_fuel_consumption(
    messages: dict[FrameType, bytearray]
) -> None:
    """Test that power, fan power and fuel consumption keys are not
    present in the device data if they are unavailable.
    """
    test_message = messages[FrameType.MESSAGE_SENSOR_DATA]
    for index in (INDEX_FAN_POWER, INDEX_FUEL_CONSUMPTION, INDEX_POWER):
        for byte in range(4):
            test_message[index + byte] = 0xFF

    frame = SensorDataMessage(message=test_message)
    assert ATTR_FAN_POWER not in frame.data
    assert ATTR_FUEL_CONSUMPTION not in frame.data
    assert ATTR_POWER not in frame.data


def test_current_data_without_thermostats(
    sensor_data_without_thermostats: bytearray,
) -> None:
    """Test that thermostats key is not present in the device data
    if thermostats data is unavailable.
    """
    frame = SensorDataMessage(message=sensor_data_without_thermostats)
    assert ATTR_THERMOSTAT_SENSORS not in frame.data
