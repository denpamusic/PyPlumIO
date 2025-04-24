"""Contains thermostat parameter descriptors."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from typing import TYPE_CHECKING

from dataslots import dataslots

from pyplumio.const import (
    ATTR_INDEX,
    ATTR_OFFSET,
    ATTR_SIZE,
    ATTR_VALUE,
    FrameType,
    UnitOfMeasurement,
)
from pyplumio.frames import Request
from pyplumio.parameters import (
    Number,
    NumberDescription,
    Parameter,
    ParameterDescription,
    ParameterValues,
    Switch,
    SwitchDescription,
)

if TYPE_CHECKING:
    from pyplumio.devices.thermostat import Thermostat


@dataclass
class ThermostatParameterDescription(ParameterDescription):
    """Represents a thermostat parameter description."""

    __slots__ = ()

    size: int = 1


class ThermostatParameter(Parameter):
    """Represents a thermostat parameter."""

    __slots__ = ("offset",)

    device: Thermostat
    description: ThermostatParameterDescription
    offset: int

    def __init__(
        self,
        device: Thermostat,
        description: ThermostatParameterDescription,
        values: ParameterValues | None = None,
        index: int = 0,
        offset: int = 0,
    ) -> None:
        """Initialize a new thermostat parameter."""
        self.offset = offset
        super().__init__(device, description, values, index)

    async def create_request(self) -> Request:
        """Create a request to change the parameter."""
        return await Request.create(
            FrameType.REQUEST_SET_THERMOSTAT_PARAMETER,
            recipient=self.device.parent.address,
            data={
                # Increase the index by one to account for thermostat
                # profile, which is being set at ecoMAX device level.
                ATTR_INDEX: self._index + 1,
                ATTR_VALUE: self.values.value,
                ATTR_OFFSET: self.offset,
                ATTR_SIZE: self.description.size,
            },
        )


@dataslots
@dataclass
class ThermostatNumberDescription(ThermostatParameterDescription, NumberDescription):
    """Represent a thermostat number description."""


class ThermostatNumber(ThermostatParameter, Number):
    """Represents a thermostat number."""

    __slots__ = ()

    description: ThermostatNumberDescription


@dataslots
@dataclass
class ThermostatSwitchDescription(ThermostatParameterDescription, SwitchDescription):
    """Represents a thermostat switch description."""


class ThermostatSwitch(ThermostatParameter, Switch):
    """Represents a thermostat switch."""

    __slots__ = ()

    description: ThermostatSwitchDescription


PARAMETER_TYPES: list[ThermostatParameterDescription] = [
    ThermostatNumberDescription(
        name="mode",
    ),
    ThermostatNumberDescription(
        name="party_target_temp",
        size=2,
        step=0.1,
        unit_of_measurement=UnitOfMeasurement.CELSIUS,
    ),
    ThermostatNumberDescription(
        name="holidays_target_temp",
        size=2,
        step=0.1,
        unit_of_measurement=UnitOfMeasurement.CELSIUS,
    ),
    ThermostatNumberDescription(
        name="correction",
        unit_of_measurement=UnitOfMeasurement.CELSIUS,
    ),
    ThermostatNumberDescription(
        name="away_timer",
        unit_of_measurement=UnitOfMeasurement.DAYS,
    ),
    ThermostatNumberDescription(
        name="airing_timer",
        unit_of_measurement=UnitOfMeasurement.DAYS,
    ),
    ThermostatNumberDescription(
        name="party_timer",
        unit_of_measurement=UnitOfMeasurement.DAYS,
    ),
    ThermostatNumberDescription(
        name="holidays_timer",
        unit_of_measurement=UnitOfMeasurement.DAYS,
    ),
    ThermostatNumberDescription(
        name="hysteresis",
        step=0.1,
        unit_of_measurement=UnitOfMeasurement.CELSIUS,
    ),
    ThermostatNumberDescription(
        name="day_target_temp",
        size=2,
        step=0.1,
        unit_of_measurement=UnitOfMeasurement.CELSIUS,
    ),
    ThermostatNumberDescription(
        name="night_target_temp",
        size=2,
        step=0.1,
        unit_of_measurement=UnitOfMeasurement.CELSIUS,
    ),
    ThermostatNumberDescription(
        name="antifreeze_target_temp",
        size=2,
        step=0.1,
        unit_of_measurement=UnitOfMeasurement.CELSIUS,
    ),
    ThermostatNumberDescription(
        name="heating_target_temp",
        size=2,
        step=0.1,
        unit_of_measurement=UnitOfMeasurement.CELSIUS,
    ),
    ThermostatNumberDescription(
        name="heating_timer",
    ),
    ThermostatNumberDescription(
        name="off_timer",
    ),
]


@cache
def get_thermostat_parameter_types() -> list[ThermostatParameterDescription]:
    """Return cached thermostat parameter types for specific product."""
    return PARAMETER_TYPES


__all__ = [
    "get_thermostat_parameter_types",
    "PARAMETER_TYPES",
    "ThermostatNumber",
    "ThermostatNumberDescription",
    "ThermostatParameter",
    "ThermostatParameterDescription",
    "ThermostatSwitch",
    "ThermostatSwitchDescription",
]
