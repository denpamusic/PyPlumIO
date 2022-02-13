"""Contains regulator parameter structure parser."""

from typing import Any, Dict, Tuple

from pyplumio import util
from pyplumio.constants import DEVICE_PARAMS


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
    offset = 3
    if parameters_number == 0:
        return data, offset

    for index in range(first_parameter, parameters_number + first_parameter):
        parameter = util.unpack_parameter(message, offset)
        if parameter is not None:
            data[DEVICE_PARAMS[index]] = parameter

        offset += 3

    return data, offset
