"""Contains mixer parameter structure parser."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from pyplumio import util
from pyplumio.const import DATA_MIXER_PARAMETERS
from pyplumio.helpers.typing import ParameterTuple

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


def from_bytes(
    message: bytearray, offset: int = 0, data: Optional[Dict[str, Any]] = None
) -> Tuple[Dict[str, Any], int]:
    """Parse bytes and return message data and offset."""
    if data is None:
        data = {}

    parameters_number = message[offset + 2]
    mixers_number = message[offset + 3]
    offset += 4
    mixer_parameters = []
    for _ in range(mixers_number):
        parameters: Dict[str, ParameterTuple] = {}
        for parameter_key in range(parameters_number):
            parameter = util.unpack_parameter(message, offset)
            if parameter is not None:
                parameter_name = f"{MIXER_PARAMETERS[parameter_key]}"
                parameters[parameter_name] = parameter

            offset += 3

        mixer_parameters.append(parameters)

    data[DATA_MIXER_PARAMETERS] = mixer_parameters

    return data, offset
