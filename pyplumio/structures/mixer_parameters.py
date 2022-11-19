"""Contains mixer parameter structure decoder."""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Tuple

from pyplumio import util
from pyplumio.const import ATTR_MIXER_PARAMETERS
from pyplumio.helpers.typing import DeviceDataType, ParameterDataType
from pyplumio.structures import StructureDecoder, make_device_data

MIXER_PARAMETERS: List[str] = [
    "mix_target_temp",
    "min_mix_target_temp",
    "max_mix_target_temp",
    "low_mix_target_temp",
    "ctrl_weather_mix",
    "mix_heat_curve",
    "parallel_offset_heat_curve",
    "weather_temp_factor",
    "mix_operation",
    "mix_insensitivity",
    "mix_therm_operation",
    "mix_therm_mode",
    "mix_off_therm_pump",
    "mix_summer_work",
]


def _decode_mixer_parameters(
    message: bytearray, offset: int, parameter_name_indexes: Iterable
) -> Tuple[Dict[str, ParameterDataType], int]:
    """Decode parameters for a single mixer."""
    mixer_parameters: Dict[str, ParameterDataType] = {}
    for index in parameter_name_indexes:
        parameter = util.unpack_parameter(message, offset)
        if parameter is not None:
            parameter_name = MIXER_PARAMETERS[index]
            mixer_parameters[parameter_name] = parameter

        offset += 3

    return mixer_parameters, offset


class MixerParametersStructure(StructureDecoder):
    """Represent mixer parameters data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        first_parameter = message[offset + 1]
        parameters_number = message[offset + 2]
        mixers_number = message[offset + 3]
        offset += 4
        mixer_parameters: List[Dict[str, ParameterDataType]] = []
        for _ in range(mixers_number):
            parameters, offset = _decode_mixer_parameters(
                message,
                offset,
                range(first_parameter, parameters_number + first_parameter),
            )
            if parameters:
                mixer_parameters.append(parameters)

        if not mixer_parameters:
            # No mixer parameters detected.
            return data, offset

        return (
            make_device_data(data, {ATTR_MIXER_PARAMETERS: mixer_parameters}),
            offset,
        )
