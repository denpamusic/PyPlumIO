"""Contains a mixer parameter structure decoder."""

from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

from pyplumio.const import (
    ATTR_DEVICE_INDEX,
    ATTR_INDEX,
    ATTR_VALUE,
    FrameType,
    ProductType,
    UnitOfMeasurement,
)
from pyplumio.frames import Request
from pyplumio.helpers.parameter import (
    SET_RETRIES,
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
from pyplumio.utils import ensure_dict

if TYPE_CHECKING:
    from pyplumio.devices.mixer import Mixer

ATTR_MIXER_PARAMETERS: Final = "mixer_parameters"

MIXER_PARAMETER_SIZE: Final = 3


@dataclass
class MixerParameterDescription(ParameterDescription):
    """Represents a mixer parameter description."""

    multiplier: float = 1.0
    offset: int = 0


class MixerParameter(Parameter):
    """Represent a mixer parameter."""

    __slots__ = ()

    device: Mixer
    description: MixerParameterDescription

    async def create_request(self) -> Request:
        """Create a request to change the parameter."""
        return await Request.create(
            FrameType.REQUEST_SET_MIXER_PARAMETER,
            recipient=self.device.parent.address,
            data={
                ATTR_INDEX: self._index,
                ATTR_VALUE: self.values.value,
                ATTR_DEVICE_INDEX: self.device.index,
            },
        )


@dataclass
class MixerNumberDescription(MixerParameterDescription, NumberDescription):
    """Represent a mixer number description."""


class MixerNumber(MixerParameter, Number):
    """Represents a mixer number."""

    __slots__ = ()

    description: MixerNumberDescription

    async def set(self, value: int | float, retries: int = SET_RETRIES) -> bool:
        """Set a parameter value."""
        value = (value + self.description.offset) / self.description.multiplier
        return await super().set(value, retries)

    @property
    def value(self) -> float:
        """Return the parameter value."""
        return (
            self.values.value - self.description.offset
        ) * self.description.multiplier

    @property
    def min_value(self) -> float:
        """Return the minimum allowed value."""
        return (
            self.values.min_value - self.description.offset
        ) * self.description.multiplier

    @property
    def max_value(self) -> float:
        """Return the maximum allowed value."""
        return (
            self.values.max_value - self.description.offset
        ) * self.description.multiplier


@dataclass
class MixerSwitchDescription(MixerParameterDescription, SwitchDescription):
    """Represents a mixer switch description."""


class MixerSwitch(MixerParameter, Switch):
    """Represents a mixer switch."""

    __slots__ = ()

    description: MixerSwitchDescription


MIXER_PARAMETERS: dict[ProductType, tuple[MixerParameterDescription, ...]] = {
    ProductType.ECOMAX_P: (
        MixerNumberDescription(
            name="mixer_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        MixerNumberDescription(
            name="min_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        MixerNumberDescription(
            name="max_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        MixerNumberDescription(
            name="thermostat_decrease_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        MixerSwitchDescription(
            name="weather_control",
        ),
        MixerNumberDescription(
            name="heating_curve",
            multiplier=0.1,
        ),
        MixerNumberDescription(
            name="heating_curve_shift",
            offset=20,
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        MixerNumberDescription(
            name="weather_factor",
        ),
        MixerNumberDescription(
            name="work_mode",
        ),
        MixerNumberDescription(
            name="mixer_input_dead_zone",
            multiplier=0.1,
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        MixerSwitchDescription(
            name="thermostat_operation",
        ),
        MixerNumberDescription(
            name="thermostat_mode",
        ),
        MixerSwitchDescription(
            name="disable_pump_on_thermostat",
        ),
        MixerSwitchDescription(
            name="summer_work",
        ),
    ),
    ProductType.ECOMAX_I: (
        MixerNumberDescription(
            name="work_mode",
        ),
        MixerNumberDescription(
            name="circuit_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        MixerNumberDescription(
            name="day_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        MixerNumberDescription(
            name="night_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        MixerNumberDescription(
            name="min_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        MixerNumberDescription(
            name="max_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        MixerSwitchDescription(
            name="summer_work",
        ),
        MixerSwitchDescription(
            name="weather_control",
        ),
        MixerNumberDescription(
            name="enable_circuit",
        ),
        MixerNumberDescription(
            name="constant_water_preset_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        MixerNumberDescription(
            name="thermostat_decrease_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        MixerNumberDescription(
            name="thermostat_correction",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        MixerSwitchDescription(
            name="thermostat_pump_lock",
        ),
        MixerNumberDescription(
            name="valve_opening_time",
            unit_of_measurement=UnitOfMeasurement.SECONDS,
        ),
        MixerNumberDescription(
            name="mixer_input_dead_zone",
            multiplier=0.1,
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        MixerNumberDescription(
            name="proportional_range",
        ),
        MixerNumberDescription(
            name="integration_time_constant",
        ),
        MixerNumberDescription(
            name="heating_curve",
            multiplier=0.1,
        ),
        MixerNumberDescription(
            name="heating_curve_shift",
            offset=20,
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        MixerNumberDescription(
            name="thermostat_mode",
        ),
        MixerNumberDescription(
            name="decreasing_constant_water_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
    ),
}


class MixerParametersStructure(StructureDecoder):
    """Represents a mixer parameters data structure."""

    _offset: int

    def _mixer_parameter(
        self, message: bytearray, start: int, end: int
    ) -> Generator[tuple[int, ParameterValues], None, None]:
        """Get a single mixer parameter."""
        for index in range(start, start + end):
            if parameter := unpack_parameter(message, self._offset):
                yield (index, parameter)

            self._offset += MIXER_PARAMETER_SIZE

    def _mixer_parameters(
        self, message: bytearray, mixers: int, start: int, end: int
    ) -> Generator[tuple[int, list[tuple[int, ParameterValues]]], None, None]:
        """Get parameters for a mixer."""
        for index in range(mixers):
            if parameters := list(self._mixer_parameter(message, start, end)):
                yield (index, parameters)

    def decode(
        self, message: bytearray, offset: int = 0, data: dict[str, Any] | None = None
    ) -> tuple[dict[str, Any], int]:
        """Decode bytes and return message data and offset."""
        start = message[offset + 1]
        end = message[offset + 2]
        mixers = message[offset + 3]
        self._offset = offset + 4
        return (
            ensure_dict(
                data,
                {
                    ATTR_MIXER_PARAMETERS: dict(
                        self._mixer_parameters(message, mixers, start, end)
                    )
                },
            ),
            self._offset,
        )
