"""Contains a thermostat parameters structure decoder."""

from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

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
    BinaryParameter,
    BinaryParameterDescription,
    Parameter,
    ParameterDescription,
    ParameterValues,
    ParameterValueType,
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

    multiplier: float = 1.0
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
        description: ParameterDescription,
        values: ParameterValues | None = None,
        index: int = 0,
        offset: int = 0,
    ):
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

    async def set(self, value: ParameterValueType, retries: int = 5) -> bool:
        """Set a parameter value."""
        if isinstance(value, (int, float)):
            value = int(value / self.description.multiplier)

        return await super().set(value, retries)

    @property
    def value(self) -> ParameterValueType:
        """Return the parameter value."""
        return self.values.value * self.description.multiplier

    @property
    def min_value(self) -> ParameterValueType:
        """Return the minimum allowed value."""
        return self.values.min_value * self.description.multiplier

    @property
    def max_value(self) -> ParameterValueType:
        """Return the maximum allowed value."""
        return self.values.max_value * self.description.multiplier


@dataclass
class ThermostatBinaryParameterDescription(
    ThermostatParameterDescription, BinaryParameterDescription
):
    """Represents a thermostat binary parameter description."""


class ThermostatBinaryParameter(BinaryParameter, ThermostatParameter):
    """Represents a thermostat binary parameter."""

    __slots__ = ()


THERMOSTAT_PARAMETERS: tuple[ThermostatParameterDescription, ...] = (
    ThermostatParameterDescription(
        name="mode",
    ),
    ThermostatParameterDescription(
        name="party_target_temp",
        size=2,
        multiplier=0.1,
        unit_of_measurement=UnitOfMeasurement.CELSIUS,
    ),
    ThermostatParameterDescription(
        name="holidays_target_temp",
        size=2,
        multiplier=0.1,
        unit_of_measurement=UnitOfMeasurement.CELSIUS,
    ),
    ThermostatParameterDescription(
        name="correction",
        unit_of_measurement=UnitOfMeasurement.CELSIUS,
    ),
    ThermostatParameterDescription(
        name="away_timer",
        unit_of_measurement=UnitOfMeasurement.DAYS,
    ),
    ThermostatParameterDescription(
        name="airing_timer",
        unit_of_measurement=UnitOfMeasurement.DAYS,
    ),
    ThermostatParameterDescription(
        name="party_timer",
        unit_of_measurement=UnitOfMeasurement.DAYS,
    ),
    ThermostatParameterDescription(
        name="holidays_timer",
        unit_of_measurement=UnitOfMeasurement.DAYS,
    ),
    ThermostatParameterDescription(
        name="hysteresis",
        multiplier=0.1,
        unit_of_measurement=UnitOfMeasurement.CELSIUS,
    ),
    ThermostatParameterDescription(
        name="day_target_temp",
        size=2,
        multiplier=0.1,
        unit_of_measurement=UnitOfMeasurement.CELSIUS,
    ),
    ThermostatParameterDescription(
        name="night_target_temp",
        size=2,
        multiplier=0.1,
        unit_of_measurement=UnitOfMeasurement.CELSIUS,
    ),
    ThermostatParameterDescription(
        name="antifreeze_target_temp",
        size=2,
        multiplier=0.1,
        unit_of_measurement=UnitOfMeasurement.CELSIUS,
    ),
    ThermostatParameterDescription(
        name="heating_target_temp",
        size=2,
        multiplier=0.1,
        unit_of_measurement=UnitOfMeasurement.CELSIUS,
    ),
    ThermostatParameterDescription(
        name="heating_timer",
    ),
    ThermostatParameterDescription(
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
        if (device := self.frame.sender_device) is not None and (
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
