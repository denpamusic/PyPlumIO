"""Contains mixer parameter structure parser."""

from typing import Any, Dict, List, Tuple

from pyplumio import util
from pyplumio.constants import DATA_MIXERS

MIXER_PARAMETERS: List[str] = [
    "mix_set_temp",
    "min_mix_set_temp",
    "max_mix_set_temp",
    "low_mix_set_temp",
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
    message: bytearray, offset: int = 0, data: Dict[str, Any] = None
) -> Tuple[Dict[str, Any], int]:
    """Parses frame message into usable data.

    Keyword arguments:
        message -- message bytes
        offset -- current data offset
    """
    if data is None:
        data = {}

    first_parameter = message[1]
    parameters_number = message[2]
    mixers_number = message[3]
    total_parameters = mixers_number * parameters_number
    offset = 4
    data[DATA_MIXERS] = []
    if parameters_number == 0:
        return data, offset

    mixer = {}
    for index in range(first_parameter, total_parameters + first_parameter):
        parameter = util.unpack_parameter(message, offset)
        if parameter is not None:
            mixer[f"{MIXER_PARAMETERS[index%total_parameters]}"] = parameter

        if (index + 1) % total_parameters == 0:
            data[DATA_MIXERS].append(mixer)
            mixer = {}

        offset += 3

    return data, offset
