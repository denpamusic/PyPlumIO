"""Contains outputs structure parser."""

from pyplumio import util


def from_bytes(message: bytearray, offset: int = 0) -> (dict, int):
    """Parses frame message into usable data.

    Keyword arguments:
    message -- ecoNET message
    offset -- current data offset
    """
    data = {}
    outputs = util.unpack_ushort(message[offset : offset + 4])
    data["fanWorks"] = bool(outputs & 0x0001)
    data["feederWorks"] = bool(outputs & 0x0002)
    data["pumpCOWorks"] = bool(outputs & 0x0004)
    data["pumpCWUWorks"] = bool(outputs & 0x0008)
    data["pumpCirculationWorks"] = bool(outputs & 0x0010)
    data["lighterWorks"] = bool(outputs & 0x0020)
    data["alarmOutputWorks"] = bool(outputs & 0x0040)
    data["outerBoilerWorks"] = bool(outputs & 0x0080)
    data["fan2ExhaustWorks"] = bool(outputs & 0x0100)
    data["feeder2AdditionalWorks"] = bool(outputs & 0x0200)
    data["feederOuterWorks"] = bool(outputs & 0x0400)
    data["pumpSolarWorks"] = bool(outputs & 0x0800)
    data["pumpFireplaceWorks"] = bool(outputs & 0x1000)
    data["contactGZCActive"] = bool(outputs & 0x2000)
    data["blowFan1Active"] = bool(outputs & 0x4000)
    data["blowFan2Active"] = bool(outputs & 0x8000)
    offset += 4

    return data, offset
