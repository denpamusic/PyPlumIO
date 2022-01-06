import functools
from os import name, system
import socket
import struct

DEGREE_SIGN = '\N{DEGREE SIGN}'
unpack_float = struct.Struct('<f').unpack
pack_header = struct.Struct('<BH4B').pack_into
unpack_header = struct.Struct('<BH4B').unpack_from

def crc(data: bytearray) -> int:
    return functools.reduce(lambda x, y: x^y, data)

def to_hex(data: bytearray) -> str:
    return [f'{data[i]:02X}' for i in range(0, len(data))]

def unpack_ushort(data: bytearray) -> int:
    return int.from_bytes(data, byteorder = 'little', signed = False)

def dump_dictionary(dictionary: dict) -> None:
    for key, value in dictionary.items():
        print(f'{key}: {str(value)}')

def ip_to_bytes(address: str) -> bytearray:
    return socket.inet_aton(address)

def ip_from_bytes(data: bytearray) -> str:
    return socket.inet_ntoa(data)

def append_bytes(arr, data) -> None:
    return [ arr.append(ord(b)) for b in data ]

def merge(defaults: dict, options: dict) -> dict:
    if not options:
        return defaults

    for key in defaults.keys():
        if not key in options:
            options[key] = defaults[key]

    return options

def check_parameter(data: bytearray) -> bool:
    for byte in data:
        if byte != 0xFF:
            return True

    return False

def uid_stamp(message: str) -> str:
    crc_ = 0xA3A3
    for byte in message:
        int_ = ord(byte)
        crc_ = crc_^int_
        for i in range(8):
            if crc_&1:
                crc_ = (crc_>>1)^0xA001
            else:
                crc_ = crc_>>1

    return chr(crc_%256) + chr((crc_//256)%256)

def uid_bits_to_char(number: int) -> str:
    if number < 0 or number >= 32:
        return '#'

    if number < 10:
        return chr(ord('0') + number)

    char = chr(ord('A') + number - 10)

    return 'Z' if char == 'O' else char

def clear_screen() -> None:
    if name == 'nt':
        _ = system('cls')
    else:
        _ = system('clear')

def is_working(state: bool) -> str:
    return 'working' if state else 'stopped'

def celsius(number) -> str:
    return f'{str(round(number, 2))} {DEGREE_SIGN}C'

def kw(number) -> str:
    return str(round(number, 2)) + ' kW'

def percent(number) -> str:
    return str(round(number, 2)) + ' %'

def kgh(number) -> str:
    return str(round(number, 2)) + ' kg/h'
