"""Contains structure classes, that are used to parse frames."""

from __future__ import annotations

import math
import struct

from . import util
from .constants import TEMP_NAMES


class FrameVersions():
    """Used to parse versioning data in CurrentData
    and RegData responses.
    """

    def from_bytes(self, message: bytearray,
            offset: int = 0) -> (list, int):
        """Parses frame message into usable data.

        Keyword arguments:
        message -- ecoNET message
        offset -- current data offset
        """
        data = {}
        frames_number = message[offset]
        offset += 1
        for _ in range(frames_number):
            frame_type = message[offset]
            version = util.unpack_ushort(message[offset+1 : offset+3])
            data[frame_type] = version
            offset += 3

        return data, offset

class Outputs():
    """Used to parse output structure for CurrentData message."""

    def from_bytes(self, message: bytearray,
            offset: int = 0) -> (dict, int):
        """Parses frame message into usable data.

        Keyword arguments:
        message -- ecoNET message
        offset -- current data offset
        """
        data = {}
        outputs = util.unpack_ushort(message[offset : offset+4])
        data['fanWorks'] = bool(outputs&0x0001)
        data['feederWorks'] = bool(outputs&0x0002)
        data['pumpCOWorks'] = bool(outputs&0x0004)
        data['pumpCWUWorks'] = bool(outputs&0x0008)
        data['pumpCirculationWorks'] = bool(outputs&0x0010)
        data['lighterWorks'] = bool(outputs&0x0020)
        data['alarmOutputWorks'] = bool(outputs&0x0040)
        data['outerBoilerWorks'] = bool(outputs&0x0080)
        data['fan2ExhaustWorks'] = bool(outputs&0x0100)
        data['feeder2AdditionalWorks'] = bool(outputs&0x0200)
        data['feederOuterWorks'] = bool(outputs&0x0400)
        data['pumpSolarWorks'] = bool(outputs&0x0800)
        data['pumpFireplaceWorks'] = bool(outputs&0x1000)
        data['contactGZCActive'] = bool(outputs&0x2000)
        data['blowFan1Active'] = bool(outputs&0x4000)
        data['blowFan2Active'] = bool(outputs&0x8000)
        offset += 4

        return data, offset

class OutputFlags():
    """Parses output flags structure for CurrentData message."""

    def from_bytes(self, message: bytearray,
            offset: int = 0) -> (dict, int):
        """Parses frame message into usable data.

        Keyword arguments:
        message -- ecoNET message
        offset -- current data offset
        """
        data = {}
        output_flags = util.unpack_ushort(message[offset : offset+4])
        data['pumpCO'] = bool(output_flags&0x004)
        data['pumpCWU'] = bool(output_flags&0x008)
        data['pumpCirculation'] = bool(output_flags&0x010)
        data['pumpSolar'] = bool(output_flags&0x800)
        offset += 4

        return data, offset

class Temperatures():
    """Parses temperature structure for CurrentData message."""

    def from_bytes(self, message: bytearray,
            offset: int = 0) -> (dict, int):
        """Parses frame message into usable data.

        Keyword arguments:
        message -- ecoNET message
        offset -- current data offset
        """
        data = {}
        temp_number = message[offset]
        offset += 1
        for _ in range(temp_number):
            index = message[offset]
            temp = util.unpack_float(message[offset + 1 : offset + 5])[0]
            if ((not math.isnan(temp))
                and index < len(TEMP_NAMES)
                and index >= 0):
                # Temperature exists and index is in the correct range.
                data[TEMP_NAMES[index]] = temp

            offset += 5

        return data, offset

class Alarms:
    """Parses alarm structure for CurrentData message."""

    def from_bytes(self, message: bytearray,
            offset: int = 0) -> (dict, int):
        """Parses frame message into usable data.

        Keyword arguments:
        message -- ecoNET message
        offset -- current data offset
        """
        data = {}
        alarms_number = message[offset]
        offset += alarms_number + 1

        return data, offset

class Versions:
    """Parses versions structure for CurrentData message."""

    _modules: list = (
        'moduleASoftVer',
        'moduleBSoftVer',
        'moduleCSoftVer',
        'moduleLambdaSoftVer',
        'moduleEcoSTERSoftVer',
        'modulePanelSoftVer'
    )

    def from_bytes(self, message: bytearray,
            offset: int = 0) -> (dict, int):
        """Parses frame message into usable data.

        Keyword arguments:
        message -- ecoNET message
        offset -- current data offset
        """
        data = {}
        for module in self._modules:
            if module == 'moduleASoftVer':
                version_data = struct.unpack('<BBBBB',
                    message[offset : offset+5])
                version1 = '.'.join(map(str, version_data[:3]))
                version2 = '.' + chr(version_data[3])
                version3 = str(version_data[4])
                data[module] = version1 + version2 + version3
                offset += 5
                continue

            if message[offset] == 0xFF:
                data[module] = None
                offset += 1
            else:
                data[module] = '.'.join(map(str,
                    struct.unpack('<BBB', message[offset : offset + 3])))
                offset += 3

        return data, offset

class Lambda:
    """Parses lambda structure for CurrentData message."""

    def from_bytes(self, message: bytearray,
            offset: int = 0) -> (dict, int):
        """Parses frame message into usable data.

        Keyword arguments:
        message -- ecoNET message
        offset -- current data offset
        """
        data = {}
        if message[offset] == 0xFF:
            offset += 1
            return data, offset

        data['lambdaStatus'] = message[offset]
        data['lambdaSet'] = message[offset+1]
        lambda_level = util.unpack_ushort( message[offset+2 : offset+4 ] )
        if math.isnan(lambda_level):
            lambda_level = None

        data['lambdaLevel'] = lambda_level
        offset += 4

        return data, offset

class Thermostats:
    """Parses thermostats structure for CurrentData message."""

    def from_bytes(self, message: bytearray,
            offset: int = 0) -> (list, int):
        """Parses frame message into usable data.

        Keyword arguments:
        message -- ecoNET message
        offset -- current data offset
        """
        data = []
        if message[offset] == 0xFF:
            offset += 1
            return offset

        therm_contacts = message[offset]
        offset += 1
        therm_number = message[offset]
        offset += 1
        if therm_number > 0:
            contact_mask = 1
            schedule_mask = 1 << 3
            for therm in range(1, therm_number + 1):
                therm = {}
                therm['ecoSterContacts'] = bool(therm_contacts&contact_mask)
                therm['ecoSterDaySched'] = bool(therm_contacts&schedule_mask)
                therm['ecoSterMode'] = bool(message[offset])
                therm['ecoSterTemp'] = util.unpack_float(
                    message[offset+1 : offset+5])[0]
                therm['ecoSterSetTemp'] = util.unpack_float(
                    message[offset+5 : offset+9])[0]
                data.append(therm)
                offset += 9
                contact_mask = contact_mask << 1
                schedule_mask = schedule_mask << 1

        return data, offset

class Mixers:
    """Parses mixers structure for CurrentData message."""

    def from_bytes( self, message: bytearray,
            offset: int = 0 ) -> (list, int):
        """Parses frame message into usable data.

        Keyword arguments:
        message -- ecoNET message
        offset -- current data offset
        """
        data = []
        mixers_number = message[offset]
        offset += 1
        if mixers_number > 0:
            for _ in range(1, mixers_number+1):
                mixer = {}
                mixer['mixerTemp'] = util.unpack_float(
                    message[offset : offset+4])[0]
                mixer['mixerSetTemp'] = message[offset+4]
                mixer_outputs = message[offset+6]
                mixer['mixerPumpWorks'] = bool(mixer_outputs&0x01)
                data.append(mixer)
                offset += 8

        return data, offset

class UID:
    """Parses UID string for UID response message."""

    UID_BASE: int = 32
    UID_BASE_BITS: int = 5
    CHAR_BITS: int = 8

    def from_bytes(self, message: bytearray,
            offset: int = 0) -> (str, int):
        """Parses frame message into usable data.

        Keyword arguments:
        message -- ecoNET message
        offset -- current data offset
        """
        uid_length = message[offset]
        offset += 1
        uid = message[offset : uid_length+offset].decode()
        offset += uid_length
        input_ = uid + util.uid_stamp(uid)
        input_length = len(input_)*self.CHAR_BITS
        output = []
        output_length = input_length//self.UID_BASE_BITS
        if input_length % self.UID_BASE_BITS:
            output_length += 1

        conv_int = 0
        conv_size =  0
        j = 0
        for _ in range(output_length):
            if conv_size < self.UID_BASE_BITS and j < len(input_):
                conv_int += (ord(input_[j])<<conv_size)
                conv_size += self.CHAR_BITS
                j += 1

            char_code = conv_int % self.UID_BASE
            conv_int //= self.UID_BASE
            conv_size -= self.UID_BASE_BITS
            output.insert(0, util.uid_bits_to_char(char_code))

        return ''.join(output), offset

class VarString:
    """Parses variable length string."""

    def from_bytes(self, message: bytearray,
            offset: int = 0 ) -> (str, int):
        """Parses frame message into usable data.

        Keyword arguments:
        message -- ecoNET message
        offset -- current data offset
        """
        string_length = message[offset]
        offset += 1

        return message[offset : offset+string_length+1].decode()
