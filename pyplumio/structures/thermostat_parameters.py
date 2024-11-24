"""Contains a thermostat parameters structure decoder."""

from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

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
from pyplumio.helpers.parameter import (
    Number,
    NumberDescription,
    Parameter,
    ParameterDescription,
    ParameterValues,
    Switch,
    SwitchDescription,
    unpack_parameter,
)
from pyplumio.structures import StructureDecoder
from pyplumio.structures.thermostat_sensors import ATTR_THERMOSTATS_AVAILABLE
from pyplumio.utils import ensure_dict

if TYPE_CHECKING:
    from pyplumio.devices.thermostat import Thermostat


ATTR_THERMOSTAT_PROFILE: Final = "thermostat_profile"
ATTR_THERMOSTAT_PARAMETERS: Final = "thermostat_parameters"

THERMOSTAT_PARAMETER_SIZE: Final = 3


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

    async def create_refresh_request(self) -> Request:
        """Create a request to refresh the parameter."""
        return await Request.create(
            FrameType.REQUEST_THERMOSTAT_PARAMETERS,
            recipient=self.device.parent.address,
        )

    @property
    def is_tracking_changes(self) -> bool:
        """Return True if remote's tracking changes, False otherwise."""
        return self.device.parent.has_frame_version(
            FrameType.REQUEST_THERMOSTAT_PARAMETERS
        )


@dataslots
@dataclass
class ThermostatNumberDescription(ThermostatParameterDescription, NumberDescription):
    """Represent a thermostat number description."""

    multiplier: float = 1.0
    precision: int = 6


class ThermostatNumber(ThermostatParameter, Number):
    """Represents a thermostat number."""

    __slots__ = ()

    description: ThermostatNumberDescription

    async def set(
        self, value: int | float, retries: int = 5, timeout: float = 5.0
    ) -> bool:
        """Set a parameter value."""
        value = round(value / self.description.multiplier, self.description.precision)
        return await super().set(value, retries, timeout)

    @property
    def value(self) -> float:
        """Return the value."""
        value = self.values.value * self.description.multiplier
        return round(value, self.description.precision)

    @property
    def min_value(self) -> float:
        """Return the minimum allowed value."""
        value = self.values.min_value * self.description.multiplier
        return round(value, self.description.precision)

    @property
    def max_value(self) -> float:
        """Return the maximum allowed value."""
        value = self.values.max_value * self.description.multiplier
        return round(value, self.description.precision)


@dataslots
@dataclass
class ThermostatSwitchDescription(ThermostatParameterDescription, SwitchDescription):
    """Represents a thermostat switch description."""


class ThermostatSwitch(ThermostatParameter, Switch):
    """Represents a thermostat switch."""

    __slots__ = ()

    description: ThermostatSwitchDescription


THERMOSTAT_PARAMETERS: tuple[ThermostatParameterDescription, ...] = (
    ThermostatNumberDescription(
        name="mode",
    ),
    ThermostatNumberDescription(
        name="party_target_temp",
        size=2,
        multiplier=0.1,
        unit_of_measurement=UnitOfMeasurement.CELSIUS,
    ),
    ThermostatNumberDescription(
        name="holidays_target_temp",
        size=2,
        multiplier=0.1,
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
        multiplier=0.1,
        unit_of_measurement=UnitOfMeasurement.CELSIUS,
    ),
    ThermostatNumberDescription(
        name="day_target_temp",
        size=2,
        multiplier=0.1,
        unit_of_measurement=UnitOfMeasurement.CELSIUS,
    ),
    ThermostatNumberDescription(
        name="night_target_temp",
        size=2,
        multiplier=0.1,
        unit_of_measurement=UnitOfMeasurement.CELSIUS,
    ),
    ThermostatNumberDescription(
        name="antifreeze_target_temp",
        size=2,
        multiplier=0.1,
        unit_of_measurement=UnitOfMeasurement.CELSIUS,
    ),
    ThermostatNumberDescription(
        name="heating_target_temp",
        size=2,
        multiplier=0.1,
        unit_of_measurement=UnitOfMeasurement.CELSIUS,
    ),
    ThermostatNumberDescription(
        name="heating_timer",
    ),
    ThermostatNumberDescription(
        name="off_timer",
    ),
)


class ThermostatParametersStructure(StructureDecoder):
    """Represents a thermostat parameters data structure."""

    __slots__ = ("_offset",)

    _offset: int

    def _thermostat_parameter(
        self, message: bytearray, thermostats: int, start: int, end: int
    ) -> Generator[tuple[int, ParameterValues], None, None]:
        """Get a single thermostat parameter."""
        for index in range(start, (start + end) // thermostats):
            description = THERMOSTAT_PARAMETERS[index]
            if parameter := unpack_parameter(
                message, self._offset, size=description.size
            ):
                yield (index, parameter)

            self._offset += THERMOSTAT_PARAMETER_SIZE * description.size

    def _thermostat_parameters(
        self, message: bytearray, thermostats: int, start: int, end: int
    ) -> Generator[tuple[int, list[tuple[int, ParameterValues]]], None, None]:
        """Get parameters for a thermostat."""
        for index in range(thermostats):
            if parameters := list(
                self._thermostat_parameter(message, thermostats, start, end)
            ):
                yield (index, parameters)

    def decode(
        self, message: bytearray, offset: int = 0, data: dict[str, Any] | None = None
    ) -> tuple[dict[str, Any], int]:
        """Decode bytes and return message data and offset."""
        if (device := self.frame.handler) is not None and (
            thermostats := device.get_nowait(ATTR_THERMOSTATS_AVAILABLE, 0)
        ) == 0:
            return (
                ensure_dict(data, {ATTR_THERMOSTAT_PARAMETERS: None}),
                offset,
            )

        start = message[offset + 1]
        end = message[offset + 2]
        offset += 3
        thermostat_profile = unpack_parameter(message, offset)
        self._offset = offset + THERMOSTAT_PARAMETER_SIZE
        return (
            ensure_dict(
                data,
                {
                    ATTR_THERMOSTAT_PROFILE: thermostat_profile,
                    ATTR_THERMOSTAT_PARAMETERS: dict(
                        self._thermostat_parameters(message, thermostats, start, end)
                    ),
                },
            ),
            self._offset,
        )
