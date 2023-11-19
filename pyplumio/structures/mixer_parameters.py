"""Contains a mixer parameter structure decoder."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, Generator

from pyplumio.const import (
    ATTR_DEVICE_INDEX,
    ATTR_INDEX,
    ATTR_VALUE,
    ProductType,
    UnitOfMeasurement,
)
from pyplumio.frames import Request
from pyplumio.helpers.factory import factory
from pyplumio.helpers.parameter import (
    BinaryParameter,
    BinaryParameterDescription,
    Parameter,
    ParameterDescription,
    ParameterValues,
    unpack_parameter,
)
from pyplumio.helpers.typing import EventDataType, ParameterValueType
from pyplumio.structures import StructureDecoder
from pyplumio.utils import ensure_dict

if TYPE_CHECKING:
    from pyplumio.devices.mixer import Mixer

ATTR_MIXER_PARAMETERS: Final = "mixer_parameters"

MIXER_PARAMETER_SIZE: Final = 3


class MixerParameter(Parameter):
    """Represents a mixer parameter."""

    __slots__ = ()

    device: Mixer
    description: MixerParameterDescription

    async def set(self, value: ParameterValueType, retries: int = 5) -> bool:
        """Set a parameter value."""
        if isinstance(value, (int, float)):
            value = int((value + self.description.offset) / self.description.multiplier)

        return await super().set(value, retries)

    @property
    def value(self) -> ParameterValueType:
        """A parameter value."""
        return (
            self.values.value - self.description.offset
        ) * self.description.multiplier

    @property
    def min_value(self) -> ParameterValueType:
        """Minimum allowed value."""
        return (
            self.values.min_value - self.description.offset
        ) * self.description.multiplier

    @property
    def max_value(self) -> ParameterValueType:
        """Maximum allowed value."""
        return (
            self.values.max_value - self.description.offset
        ) * self.description.multiplier

    @property
    def request(self) -> Request:
        """A request to change the parameter."""
        return factory(
            "frames.requests.SetMixerParameterRequest",
            recipient=self.device.parent.address,
            data={
                ATTR_INDEX: self._index,
                ATTR_VALUE: self.values.value,
                ATTR_DEVICE_INDEX: self.device.index,
            },
        )


class MixerBinaryParameter(BinaryParameter, MixerParameter):
    """Represents a mixer binary parameter."""


@dataclass
class MixerParameterDescription(ParameterDescription):
    """Represents a mixer parameter description."""

    multiplier: float = 1
    offset: int = 0


@dataclass
class MixerBinaryParameterDescription(
    MixerParameterDescription, BinaryParameterDescription
):
    """Represents a mixer binary parameter description."""


MIXER_PARAMETERS: dict[ProductType, tuple[MixerParameterDescription, ...]] = {
    ProductType.ECOMAX_P: (
        MixerParameterDescription(
            name="mixer_target_temp", unit_of_measurement=UnitOfMeasurement.CELSIUS
        ),
        MixerParameterDescription(
            name="min_target_temp", unit_of_measurement=UnitOfMeasurement.CELSIUS
        ),
        MixerParameterDescription(
            name="max_target_temp", unit_of_measurement=UnitOfMeasurement.CELSIUS
        ),
        MixerParameterDescription(
            name="thermostat_decrease_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        MixerBinaryParameterDescription(name="weather_control"),
        MixerParameterDescription(name="heating_curve", multiplier=0.1),
        MixerParameterDescription(
            name="heating_curve_shift",
            offset=20,
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        MixerParameterDescription(name="weather_factor"),
        MixerParameterDescription(name="work_mode"),
        MixerParameterDescription(
            name="mixer_input_dead_zone",
            multiplier=0.1,
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        MixerBinaryParameterDescription(name="thermostat_operation"),
        MixerParameterDescription(name="thermostat_mode"),
        MixerBinaryParameterDescription(name="disable_pump_on_thermostat"),
        MixerBinaryParameterDescription(name="summer_work"),
    ),
    ProductType.ECOMAX_I: (
        MixerParameterDescription(name="work_mode"),
        MixerParameterDescription(
            name="circuit_target_temp", unit_of_measurement=UnitOfMeasurement.CELSIUS
        ),
        MixerParameterDescription(
            name="day_target_temp", unit_of_measurement=UnitOfMeasurement.CELSIUS
        ),
        MixerParameterDescription(
            name="night_target_temp", unit_of_measurement=UnitOfMeasurement.CELSIUS
        ),
        MixerParameterDescription(
            name="min_target_temp", unit_of_measurement=UnitOfMeasurement.CELSIUS
        ),
        MixerParameterDescription(
            name="max_target_temp", unit_of_measurement=UnitOfMeasurement.CELSIUS
        ),
        MixerBinaryParameterDescription(name="summer_work"),
        MixerBinaryParameterDescription(name="weather_control"),
        MixerParameterDescription(name="enable_circuit"),
        MixerParameterDescription(
            name="constant_water_preset_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        MixerParameterDescription(
            name="thermostat_decrease_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        MixerParameterDescription(
            name="thermostat_correction", unit_of_measurement=UnitOfMeasurement.CELSIUS
        ),
        MixerBinaryParameterDescription(name="thermostat_pump_lock"),
        MixerParameterDescription(
            name="valve_opening_time", unit_of_measurement=UnitOfMeasurement.SECONDS
        ),
        MixerParameterDescription(
            name="mixer_input_dead_zone",
            multiplier=0.1,
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        MixerParameterDescription(name="proportional_range"),
        MixerParameterDescription(name="integration_time_constant"),
        MixerParameterDescription(name="heating_curve", multiplier=0.1),
        MixerParameterDescription(
            name="heating_curve_shift",
            offset=20,
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        MixerParameterDescription(name="thermostat_mode"),
        MixerParameterDescription(
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
        self, message: bytearray, offset: int = 0, data: EventDataType | None = None
    ) -> tuple[EventDataType, int]:
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
