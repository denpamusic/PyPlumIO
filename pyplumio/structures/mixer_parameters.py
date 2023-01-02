"""Contains mixer parameter structure decoder."""
from __future__ import annotations

from typing import Final, Iterable, List, Optional, Tuple

from pyplumio import util
from pyplumio.helpers.typing import DeviceDataType, ParameterDataType
from pyplumio.structures import StructureDecoder, ensure_device_data

ATTR_MIXER_PARAMETERS: Final = "mixer_parameters"

ECOMAX_P_MIXER_PARAMETERS: Tuple[str, ...] = (
    "mixer_target_temp",
    "min_target_temp",
    "max_target_temp",
    "low_target_temp",
    "weather_control",
    "heat_curve",
    "parallel_offset_heat_curve",
    "weather_temp_factor",
    "work_mode",
    "insensitivity",
    "therm_operation",
    "therm_mode",
    "off_therm_pump",
    "summer_work",
)

ECOMAX_I_MIXER_PARAMETERS: Tuple[str, ...] = (
    "work_mode",
    "mixer_target_temp",
    "day_target_temp",
    "night_target_temp",
    "min_target_temp",
    "max_target_temp",
    "summer_work",
    "regulation",
    "handling",
    "therm_choice",
    "decrease_therm_temp",
    "correction_therm",
    "lock_therm",
    "open_time",
    "threshold",
    "pid_k",
    "pid_ti",
    "heat_curve",
    "parallel_heat_curve_h",
    "function_tr",
    "night_lower_water",
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

        if not parameters:
            # No mixer parameters detected.
            return data, offset

        return (
            ensure_device_data(data, {ATTR_MIXER_PARAMETERS: mixer_parameters}),
            offset,
        )
