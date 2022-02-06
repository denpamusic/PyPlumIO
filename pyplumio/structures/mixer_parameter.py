"""Contains mixer parameter structure parser."""

from pyplumio import util
from pyplumio.constants import DATA_MIXERS, MIXER_PARAMS


def from_bytes(message: bytearray, offset: int = 0, data: dict = None) -> (dict, int):
    """Parses frame message into usable data.

    Keyword arguments:
    message -- ecoNET message
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
            mixer[f"{MIXER_PARAMS[index%mixers_number]}"] = parameter

        if index % parameters_number == 0:
            data[DATA_MIXERS].append(mixer)
            mixer = {}

        offset += 3

    return data, offset