"""Contains variable string structure parser."""


def from_bytes(message: bytearray, offset: int = 0) -> (str, int):
    """Parses frame message into usable data.

    Keyword arguments:
    message -- ecoNET message
    offset -- current data offset
    """
    string_length = message[offset]
    offset += 1

    return message[offset : offset + string_length + 1].decode()
