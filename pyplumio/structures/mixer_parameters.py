"""Contains a mixer parameter structure decoder."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, Generator

from pyplumio.const import ATTR_DEVICE_INDEX, ATTR_INDEX, ATTR_VALUE, ProductType
from pyplumio.frames import Request
from pyplumio.helpers.factory import factory
from pyplumio.helpers.parameter import (
    BinaryParameter,
    Parameter,
    ParameterDescription,
    unpack_parameter,
)
from pyplumio.helpers.typing import (
    EventDataType,
    ParameterTupleType,
    ParameterValueType,
)
from pyplumio.structures import StructureDecoder, ensure_device_data

if TYPE_CHECKING:
    from pyplumio.devices.mixer import Mixer

ATTR_MIXER_PARAMETERS: Final = "mixer_parameters"

MIXER_PARAMETER_SIZE: Final = 3


class MixerParameter(Parameter):
    """Represents a mixer parameter."""

    device: Mixer
    description: MixerParameterDescription

    async def set(self, value: ParameterValueType, retries: int = 5) -> bool:
        """Set a parameter value."""
        if isinstance(value, (int, float)):
            value *= self.description.multiplier
            value -= self.description.offset

        return await super().set(value, retries)

    @property
    def value(self) -> ParameterValueType:
        """A parameter value."""
        return (self._value / self.description.multiplier) - self.description.offset

    @property
    def min_value(self) -> ParameterValueType:
        """Minimum allowed value."""
        return (self._min_value / self.description.multiplier) - self.description.offset

    @property
    def max_value(self) -> ParameterValueType:
        """Maximum allowed value."""
        return (self._max_value / self.description.multiplier) - self.description.offset

    @property
    def request(self) -> Request:
        """A request to change the parameter."""
        return factory(
            "frames.requests.SetMixerParameterRequest",
            recipient=self.device.parent.address,
            data={
                ATTR_INDEX: self._index,
                ATTR_VALUE: self._value,
                ATTR_DEVICE_INDEX: self.device.index,
            },
        )


class MixerBinaryParameter(BinaryParameter, MixerParameter):
    """Represents a mixer binary parameter."""


@dataclass
class MixerParameterDescription(ParameterDescription):
    """Represents a mixer parameter description."""

    cls: type[MixerParameter] = MixerParameter
    multiplier: int = 1
    offset: int = 0


MIXER_PARAMETERS: dict[ProductType, tuple[MixerParameterDescription, ...]] = {
    ProductType.ECOMAX_P: (
        MixerParameterDescription(name="mixer_target_temp"),
        MixerParameterDescription(name="min_target_temp"),
        MixerParameterDescription(name="max_target_temp"),
        MixerParameterDescription(name="low_target_temp"),
        MixerParameterDescription(name="weather_control", cls=MixerBinaryParameter),
        MixerParameterDescription(name="heat_curve", multiplier=10),
        MixerParameterDescription(name="parallel_offset_heat_curve"),
        MixerParameterDescription(name="weather_temp_factor"),
        MixerParameterDescription(name="work_mode"),
        MixerParameterDescription(name="insensitivity", multiplier=10),
        MixerParameterDescription(name="therm_operation"),
        MixerParameterDescription(name="therm_mode"),
        MixerParameterDescription(name="off_therm_pump", cls=MixerBinaryParameter),
        MixerParameterDescription(name="summer_work", cls=MixerBinaryParameter),
    ),
    ProductType.ECOMAX_I: (
        MixerParameterDescription(name="work_mode"),
        MixerParameterDescription(name="mixer_target_temp"),
        MixerParameterDescription(name="day_target_temp"),
        MixerParameterDescription(name="night_target_temp"),
        MixerParameterDescription(name="min_target_temp"),
        MixerParameterDescription(name="max_target_temp"),
        MixerParameterDescription(name="summer_work", cls=MixerBinaryParameter),
        MixerParameterDescription(name="weather_control", cls=MixerBinaryParameter),
        MixerParameterDescription(name="adjustment_method"),
        MixerParameterDescription(name="constant_water_preset_temp"),
        MixerParameterDescription(name="decreasing_constant_water_temp"),
        MixerParameterDescription(name="thermostat_correction"),
        MixerParameterDescription(
            name="thermostat_pump_lock", cls=MixerBinaryParameter
        ),
        MixerParameterDescription(name="valve_open_time"),
        MixerParameterDescription(name="threshold"),
        MixerParameterDescription(name="pid_k"),
        MixerParameterDescription(name="pid_ti"),
        MixerParameterDescription(name="heating_curve", multiplier=10),
        MixerParameterDescription(name="heating_curve_shift", offset=20),
        MixerParameterDescription(name="thermostat_function"),
        MixerParameterDescription(name="thermostat_decrease_temp"),
    ),
}


class MixerParametersStructure(StructureDecoder):
    """Represents a mixer parameters data structure."""

    _offset: int

    def _mixer_parameter(
        self, message: bytearray, start: int, end: int
    ) -> Generator[tuple[int, ParameterTupleType], None, None]:
        """Get a single mixer parameter."""
        for index in range(start, start + end):
            if parameter := unpack_parameter(message, self._offset):
                yield (index, parameter)

            self._offset += MIXER_PARAMETER_SIZE

    def _mixer_parameters(
        self, message: bytearray, mixers: int, start: int, end: int
    ) -> Generator[tuple[int, list[tuple[int, ParameterTupleType]]], None, None]:
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
            ensure_device_data(
                data,
                {
                    ATTR_MIXER_PARAMETERS: dict(
                        self._mixer_parameters(message, mixers, start, end)
                    )
                },
            ),
            self._offset,
        )
