"""Contains alarms structure parser."""


def from_bytes(message: bytearray, offset: int = 0) -> (dict, int):
    """Parses frame message into usable data.

    Keyword arguments:
    message -- ecoNET message
    offset -- current data offset
    """
    data = {}
    alarms_number = message[offset]
    offset += alarms_number + 1

    return data, offset
