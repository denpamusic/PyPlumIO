"""Contains output flags structure parser."""

from pyplumio import util


def from_bytes(message: bytearray, offset: int = 0) -> (dict, int):
    """Parses frame message into usable data.

    Keyword arguments:
    message -- ecoNET message
    offset -- current data offset
    """
    data = {}
    output_flags = util.unpack_ushort(message[offset : offset + 4])
    data["pumpCO"] = bool(output_flags & 0x004)
    data["pumpCWU"] = bool(output_flags & 0x008)
    data["pumpCirculation"] = bool(output_flags & 0x010)
    data["pumpSolar"] = bool(output_flags & 0x800)
    offset += 4

    return data, offset
