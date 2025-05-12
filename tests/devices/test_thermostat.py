"""Contains tests for the thermostat virtual device."""

import asyncio
from typing import Final

import pytest

from pyplumio.const import ATTR_SENSORS
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.devices.thermostat import Thermostat
from pyplumio.frames.messages import SensorDataMessage
from pyplumio.frames.responses import ThermostatParametersResponse
from pyplumio.parameters import ParameterValues
from pyplumio.parameters.thermostat import ThermostatNumber, ThermostatParameter
from pyplumio.structures.thermostat_parameters import ATTR_THERMOSTAT_PARAMETERS
from pyplumio.structures.thermostat_sensors import ATTR_THERMOSTAT_SENSORS
from tests.conftest import class_from_json

THERMOSTAT_INDEX: Final = 0


@pytest.fixture(name="thermostat")
def fixture_thermostat(ecomax: EcoMAX) -> Thermostat:
    """Return a Thermostat object."""
    return Thermostat(asyncio.Queue(), parent=ecomax, index=THERMOSTAT_INDEX)


@class_from_json(SensorDataMessage, "messages/sensor_data.json", arguments=("data",))
async def test_thermostat_sensors_event_listener(
    thermostat: Thermostat, sensor_data: SensorDataMessage
) -> None:
    """Test event listener for thermostat sensors."""
    thermostat_sensors_data = sensor_data.data[ATTR_SENSORS][ATTR_THERMOSTAT_SENSORS]
    thermostat.dispatch_nowait(
        ATTR_THERMOSTAT_SENSORS, thermostat_sensors_data[THERMOSTAT_INDEX]
    )
    await thermostat.wait_until_done()
    assert thermostat.data == {
        "state": 3,
        "current_temp": 43.5,
        "target_temp": 50.0,
        "contacts": True,
        "schedule": False,
        "thermostat_sensors": True,
    }


@class_from_json(
    ThermostatParametersResponse,
    "responses/thermostat_parameters.json",
    arguments=("data",),
)
@pytest.mark.parametrize(
    ("name", "cls", "values"),
    [
        (
            "mode",
            ThermostatNumber,
            ParameterValues(value=0, min_value=0, max_value=7),
        ),
        (
            "party_target_temp",
            ThermostatNumber,
            ParameterValues(value=220, min_value=100, max_value=350),
        ),
        (
            "holidays_target_temp",
            ThermostatNumber,
            ParameterValues(value=150, min_value=100, max_value=350),
        ),
        (
            "correction",
            ThermostatNumber,
            ParameterValues(value=100, min_value=60, max_value=140),
        ),
        (
            "away_timer",
            ThermostatNumber,
            ParameterValues(value=2, min_value=0, max_value=60),
        ),
        (
            "airing_timer",
            ThermostatNumber,
            ParameterValues(value=1, min_value=0, max_value=60),
        ),
        (
            "party_timer",
            ThermostatNumber,
            ParameterValues(value=1, min_value=0, max_value=60),
        ),
        (
            "holidays_timer",
            ThermostatNumber,
            ParameterValues(value=10, min_value=0, max_value=60),
        ),
        (
            "hysteresis",
            ThermostatNumber,
            ParameterValues(value=9, min_value=0, max_value=50),
        ),
        (
            "day_target_temp",
            ThermostatNumber,
            ParameterValues(value=222, min_value=100, max_value=350),
        ),
        (
            "night_target_temp",
            ThermostatNumber,
            ParameterValues(value=212, min_value=100, max_value=350),
        ),
        (
            "antifreeze_target_temp",
            ThermostatNumber,
            ParameterValues(value=90, min_value=50, max_value=300),
        ),
    ],
)
async def test_thermostat_parameters_event_listener(
    thermostat: Thermostat,
    thermostat_parameters: ThermostatParametersResponse,
    name: str,
    cls: type[ThermostatParameter],
    values: ParameterValues,
) -> None:
    """Test event listener for thermostat parameters."""
    thermostat_parameters_data = thermostat_parameters.data[ATTR_THERMOSTAT_PARAMETERS]
    thermostat.dispatch_nowait(
        ATTR_THERMOSTAT_PARAMETERS, thermostat_parameters_data[THERMOSTAT_INDEX]
    )
    await thermostat.wait_until_done()
    assert len(thermostat.data) == 13
    parameter = thermostat.get_nowait(name)
    assert isinstance(parameter, cls)
    assert parameter.values == values
