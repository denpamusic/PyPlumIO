"""Contains UID structure parser."""

from pyplumio import util
from pyplumio.constants import UID_BASE, UID_BASE_BITS, UID_CHAR_BITS


def from_bytes(message: bytearray, offset: int = 0) -> (str, int):
    """Parses frame message into usable data.

    Keyword arguments:
    message -- ecoNET message
    offset -- current data offset
    """
    uid_length = message[offset]
    offset += 1
    uid = message[offset : uid_length + offset].decode()
    offset += uid_length
    input_ = uid + util.uid_stamp(uid)
    input_length = len(input_) * UID_CHAR_BITS
    output = []
    output_length = input_length // UID_BASE_BITS
    if input_length % UID_BASE_BITS:
        output_length += 1

    conv_int = 0
    conv_size = 0
    j = 0
    for _ in range(output_length):
        if conv_size < UID_BASE_BITS and j < len(input_):
            conv_int += ord(input_[j]) << conv_size
            conv_size += UID_CHAR_BITS
            j += 1

        char_code = conv_int % UID_BASE
        conv_int //= UID_BASE
        conv_size -= UID_BASE_BITS
        output.insert(0, util.uid_5bits_to_char(char_code))

    return "".join(output), offset
