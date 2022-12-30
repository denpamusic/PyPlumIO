"""Contains mixer parameter structure decoder."""
from __future__ import annotations

from typing import Iterable, List, Optional, Tuple

from pyplumio import util
from pyplumio.const import ATTR_MIXER_PARAMETERS
from pyplumio.helpers.typing import DeviceDataType, ParameterDataType
from pyplumio.structures import StructureDecoder, ensure_device_data

ECOMAX_P_MIXER_PARAMETERS: Tuple[str, ...] = (
    "mixer_target_temp",
    "min_mixer_target_temp",
    "max_mixer_target_temp",
    "low_mixer_target_temp",
    "mixer_weather_control",
    "mixer_heat_curve",
    "mixer_parallel_offset_heat_curve",
    "mixer_weather_temp_factor",
    "mixer_work_mode",
    "mixer_insensitivity",
    "mixer_therm_operation",
    "mixer_therm_mode",
    "mixer_off_therm_pump",
    "mixer_summer_work",
)

ECOMAX_I_MIXER_PARAMETERS: Tuple[str, ...] = (
    "mixer_work_mode",
    "mixer_target_temp",
    "day_mixer_target_temp",
    "night_mixer_target_temp",
    "min_mixer_target_temp",
    "max_mixer_target_temp",
    "mixer_summer_work",
    "mixer_regulation",
    "mixer_handling",
    "mixer_therm_choice",
    "mixer_decrease_therm_temp",
    "mixer_correction_therm",
    "mixer_lock_therm",
    "mixer_open_time",
    "mixer_threshold",
    "mixer_pid_k",
    "mixer_pid_ti",
    "mixer_heat_curve",
    "mixer_parallel_heat_curve_h",
    "mixer_function_tr",
    "mixer_night_lower_water",
)


def _decode_mixer_parameters(
    message: bytearray, offset: int, parameter_name_indexes: Iterable
) -> Tuple[List[Tuple[int, ParameterDataType]], int]:
    """Decode parameters for a single mixer."""
    mixer_parameters: List[Tuple[int, ParameterDataType]] = []
    for index in parameter_name_indexes:
        parameter = util.unpack_parameter(message, offset)
        if parameter is not None:
            mixer_parameters.append((index, parameter))

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
        total_parameters_per_mixer = parameters_number + first_parameter
        offset += 4
        mixer_parameters: List[Tuple[int, List[Tuple[int, ParameterDataType]]]] = []
        for mixer_number in range(mixers_number):
            parameters, offset = _decode_mixer_parameters(
                message,
                offset,
                range(first_parameter, total_parameters_per_mixer),
            )
            if parameters:
                mixer_parameters.append((mixer_number, parameters))

        if not mixer_parameters:
            # No mixer parameters detected.
            return data, offset

        return (
            ensure_device_data(data, {ATTR_MIXER_PARAMETERS: mixer_parameters}),
            offset,
        )
