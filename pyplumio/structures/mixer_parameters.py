"""Contains mixer parameter structure decoder."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Iterable, List, Optional, Tuple, Type

from pyplumio import util
from pyplumio.const import ATTR_DEVICE_INDEX, ATTR_INDEX, ATTR_VALUE
from pyplumio.devices import Mixer
from pyplumio.frames import Request
from pyplumio.helpers.factory import factory
from pyplumio.helpers.parameter import BinaryParameter, Parameter, ParameterDescription
from pyplumio.helpers.typing import (
    DeviceDataType,
    ParameterDataType,
    ParameterValueType,
)
from pyplumio.structures import StructureDecoder, ensure_device_data

ATTR_MIXER_PARAMETERS: Final = "mixer_parameters"


class MixerParameter(Parameter):
    """Represents mixer parameter."""

    device: Mixer
    description: MixerParameterDescription

    async def set(self, value: ParameterValueType, retries: int = 5) -> bool:
        """Set parameter value."""
        if isinstance(value, (int, float)):
            value *= self.description.multiplier
            value -= self.description.offset

        return await super().set(value, retries)

    @property
    def value(self) -> ParameterValueType:
        """Return parameter value."""
        return (self._value / self.description.multiplier) - self.description.offset

    @property
    def min_value(self) -> ParameterValueType:
        """Return minimum allowed value."""
        return (self._min_value / self.description.multiplier) - self.description.offset

    @property
    def max_value(self) -> ParameterValueType:
        """Return maximum allowed value."""
        return (self._max_value / self.description.multiplier) - self.description.offset

    @property
    def request(self) -> Request:
        """Return request to change the parameter."""
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
    """Represents mixer binary parameter."""


@dataclass
class MixerParameterDescription(ParameterDescription):
    """Represent mixer parameter description."""

    cls: Type[MixerParameter] = MixerParameter
    multiplier: int = 1
    offset: int = 0


ECOMAX_P_MIXER_PARAMETERS: Tuple[MixerParameterDescription, ...] = (
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
    MixerParameterDescription(name="off_therm_pump"),
    MixerParameterDescription(name="summer_work", cls=MixerBinaryParameter),
)

ECOMAX_I_MIXER_PARAMETERS: Tuple[MixerParameterDescription, ...] = (
    MixerParameterDescription(name="work_mode"),
    MixerParameterDescription(name="mixer_target_temp"),
    MixerParameterDescription(name="day_target_temp"),
    MixerParameterDescription(name="night_target_temp"),
    MixerParameterDescription(name="min_target_temp"),
    MixerParameterDescription(name="max_target_temp"),
    MixerParameterDescription(name="summer_work", cls=MixerBinaryParameter),
    MixerParameterDescription(name="support", cls=MixerBinaryParameter),
    MixerParameterDescription(name="adjustment_method"),
    MixerParameterDescription(name="constant_water_preset_temp"),
    MixerParameterDescription(name="decreasing_constant_water_temp"),
    MixerParameterDescription(name="thermostat_correction"),
    MixerParameterDescription(name="thermostat_pump_lock", cls=MixerBinaryParameter),
    MixerParameterDescription(name="valve_open_time"),
    MixerParameterDescription(name="threshold"),
    MixerParameterDescription(name="pid_k"),
    MixerParameterDescription(name="pid_ti"),
    MixerParameterDescription(name="heating_curve", multiplier=10),
    MixerParameterDescription(name="heating_curve_shift", offset=20),
    MixerParameterDescription(name="thermostat_function"),
    MixerParameterDescription(name="thermostat_decrease_temp"),
)


def _decode_mixer_parameters(
    message: bytearray, offset: int, indexes: Iterable
) -> Tuple[List[Tuple[int, ParameterDataType]], int]:
    """Decode parameters for a single mixer."""
    parameters: List[Tuple[int, ParameterDataType]] = []
    for index in indexes:
        parameter = util.unpack_parameter(message, offset)
        if parameter is not None:
            parameters.append((index, parameter))

        offset += 3

    return parameters, offset


class MixerParametersStructure(StructureDecoder):
    """Represent mixer parameters data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        first_index = message[offset + 1]
        last_index = message[offset + 2]
        mixer_count = message[offset + 3]
        parameter_count_per_mixer = first_index + last_index
        offset += 4
        mixer_parameters: List[Tuple[int, List[Tuple[int, ParameterDataType]]]] = []
        for index in range(mixer_count):
            parameters, offset = _decode_mixer_parameters(
                message,
                offset,
                range(first_index, parameter_count_per_mixer),
            )
            if parameters:
                mixer_parameters.append((index, parameters))

        if not mixer_parameters:
            # No mixer parameters detected.
            return ensure_device_data(data, {ATTR_MIXER_PARAMETERS: None}), offset

        return (
            ensure_device_data(data, {ATTR_MIXER_PARAMETERS: mixer_parameters}),
            offset,
        )
