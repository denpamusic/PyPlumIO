"""Contains mixer parameter structure parser."""

from typing import Any, Dict, List, Optional, Tuple

from pyplumio import util
from pyplumio.constants import DATA_MIXER_PARAMETERS

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
    """Parses frame message into usable data.

    Keyword arguments:
        message -- message bytes
        offset -- current data offset
    """
    if data is None:
        data = {}

    first_parameter = message[offset + 1]
    parameters_number = message[offset + 2]
    mixers_number = message[offset + 3]
    total_parameters = mixers_number * parameters_number
    offset += 4

    mixer_parameters: List[Dict[str, Tuple[int, ...]]] = []

    if parameters_number > 0:
        mixer = {}
        for index in range(first_parameter, total_parameters + first_parameter):
            parameter = util.unpack_parameter(message, offset)
            if parameter is not None:
                mixer[f"{MIXER_PARAMETERS[index%total_parameters]}"] = parameter

            if (index + 1) % total_parameters == 0:
                mixer_parameters.append(mixer)
                mixer = {}

            offset += 3

    data[DATA_MIXER_PARAMETERS] = mixer_parameters

    return data, offset
