"""Contains regulator parameter structure parser."""

from pyplumio import util
from pyplumio.constants import EDITABLE_PARAMS


def from_bytes(message: bytearray, offset: int = 0, data: dict = None) -> (dict, int):
    """Parses frame message into usable data.

    Keyword arguments:
    message -- ecoNET message
    offset -- current data offset
    """
    if data is None:
        data = {}

    first = message[1]
    offset = 3
    parameters_number = message[2]
    if parameters_number > 0:
        for parameter in range(first, parameters_number + first):
            if parameter < len(EDITABLE_PARAMS):
                parameter_name = EDITABLE_PARAMS[parameter]
                parameter = util.unpack_parameter(message, offset)
                if parameter is not None:
                    data[parameter_name] = parameter

                offset += 3

    return data, offset
