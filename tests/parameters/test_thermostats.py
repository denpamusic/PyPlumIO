"""Contains tests for the thermostat parameter descriptors."""

import pytest

from pyplumio.const import ATTR_INDEX, ATTR_OFFSET, ATTR_SIZE, ATTR_VALUE
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.devices.thermostat import Thermostat
from pyplumio.frames.requests import SetThermostatParameterRequest
from pyplumio.parameters import ParameterValues
from pyplumio.parameters.thermostat import (
    ThermostatNumber,
    ThermostatNumberDescription,
    ThermostatSwitch,
    ThermostatSwitchDescription,
    get_thermostat_parameter_types,
)


@pytest.fixture(name="thermostat")
def fixture_thermostat(ecomax: EcoMAX) -> Thermostat:
    """Return an thermostat object."""
    return Thermostat(ecomax.queue, parent=ecomax)


async def test_mixer_parameter_create_request(thermostat: Thermostat) -> None:
    """Test create_request method for mixer parameter."""
    # Test with number.
    thermostat_number = ThermostatNumber(
        device=thermostat,
        description=ThermostatNumberDescription(name="test_number"),
        values=ParameterValues(value=10, min_value=0, max_value=20),
    )
    thermostat_number_request = await thermostat_number.create_request()
    assert isinstance(thermostat_number_request, SetThermostatParameterRequest)
    assert thermostat_number_request.data == {
        ATTR_INDEX: 1,
        ATTR_VALUE: 10,
        ATTR_OFFSET: 0,
        ATTR_SIZE: 1,
    }

    # Test with switch.
    thermostat_switch = ThermostatSwitch(
        device=thermostat,
        description=ThermostatSwitchDescription(name="test_switch"),
        values=ParameterValues(value=0, min_value=0, max_value=1),
    )
    thermostat_switch_request = await thermostat_switch.create_request()
    assert isinstance(thermostat_switch_request, SetThermostatParameterRequest)
    assert thermostat_switch_request.data == {
        ATTR_INDEX: 1,
        ATTR_VALUE: 0,
        ATTR_OFFSET: 0,
        ATTR_SIZE: 1,
    }


def test_get_thermostat_parameter_types(thermostat: Thermostat) -> None:
    """Test ecoMAX parameter types getter."""
    parameter_types_all = get_thermostat_parameter_types()
    assert len(parameter_types_all) == 15
