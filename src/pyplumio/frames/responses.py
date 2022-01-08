"""Contains response frame classes."""

import struct

from pyplumio import structures, util
from pyplumio.constants import EDITABLE_PARAMS, MODES, VERSION
from pyplumio.frame import Frame


class ProgramVersion(Frame):
    """Contains information about device software and hardware version."""

    type_: int = 0xC0

    _defaults: dict = {
        "version": VERSION,
        "struct_tag": b"\xFF\xFF",
        "struct_version": 5,
        "device_id": b"\x7A\x00",
        "processor_signature": b"\x00\x00\x00",
    }

    def create_message(self) -> bytearray:
        """Creates ProgramVersion message."""
        data = util.merge(self._defaults, self._data)
        version = data["version"].split(".")
        message = bytearray(15)
        struct.pack_into(
            "<2sB2s3sBHHH",
            message,
            0,
            data["struct_tag"],
            data["struct_version"],
            data["device_id"],
            data["processor_signature"],
            *map(int, version),
            self.sender,
        )

        return message

    def parse_message(self, message: bytearray):
        """Parses ProgramVersion message into usable data.

        Keywords arguments:
        message -- message to parse
        """
        self._data = {}
        [
            self._data["struct_tag"],
            self._data["struct_version"],
            self._data["device_id"],
            self._data["processor_signature"],
            version1,
            version2,
            version3,
            self._data["address"],
        ] = struct.unpack_from("<2sB2s3sBHHH", message)
        self._data["version"] = ".".join(map(str, [version1, version2, version3]))


class CheckDevice(Frame):
    """Contains ecoNET device information."""

    type_: int = 0xB0

    _defaults: dict = {
        "eth": {
            "ip": "192.168.1.120",
            "netmask": "255.255.255.0",
            "gateway": "192.168.1.1",
            "status": True,
        },
        "wlan": {
            "ip": "192.168.1.106",
            "netmask": "255.255.255.0",
            "gateway": "192.168.1.1",
            "status": True,
            "encryption": 4,
            "quality": 100,
            "ssid": "netfleet",
        },
        "server": {"status": True},
    }

    def create_message(self) -> bytearray:
        """Creates CheckDevice message."""
        message = bytearray()
        message += b"\x01"
        data = util.merge(self._defaults, self._data)
        eth = data["eth"]
        wlan = data["wlan"]
        server = data["server"]
        for address in ("ip", "netmask", "gateway"):
            message += util.ip_to_bytes(eth[address])

        message.append(eth["status"])
        for address in ("ip", "netmask", "gateway"):
            message += util.ip_to_bytes(wlan[address])

        message.append(wlan["status"])
        message.append(wlan["encryption"])
        message.append(wlan["quality"])
        message.append(server["status"])
        message += b"\x00" * 4
        message.append(len(wlan["ssid"]))
        message += wlan["ssid"].encode("utf-8")

        return message

    def parse_message(self, message: bytearray) -> None:
        """Parses CheckDevice message into usable data.

        Keywords arguments:
        message -- message to parse
        """
        self._data = {"eth": {}, "wlan": {}, "server": {}}
        offset = 1
        for part in ("ip", "netmask", "gateway"):
            self._data["eth"][part] = util.ip_from_bytes(message[offset : offset + 4])
            offset += 4

        self._data["eth"]["status"] = bool(message[offset])
        offset += 1
        for part in ("ip", "netmask", "gateway"):
            self._data["wlan"][part] = util.ip_from_bytes(message[offset : offset + 4])
            offset += 4

        self._data["wlan"]["status"] = bool(message[offset])
        self._data["wlan"]["encryption"] = int(message[offset + 1])
        self._data["wlan"]["quality"] = int(message[offset + 2])
        self._data["server"]["status"] = bool(message[offset + 3])
        offset += 8
        self._data["wlan"]["ssid"] = structures.VarString().from_bytes(message, offset)


class CurrentData(Frame):
    """Contains current device state data."""

    type_: int = 0x35

    def parse_message(self, message: bytearray) -> None:
        """Parses CurrentData message into usable data.

        Keywords arguments:
        message -- message to parse
        """
        offset = 0
        self._data = {}
        self._data["frame_versions"], offset = structures.FrameVersions().from_bytes(
            message, offset
        )
        self._data["mode"] = message[offset]
        self._data["modeString"] = MODES[self._data["mode"]]
        offset += 1
        self._data["outputs"], offset = structures.Outputs().from_bytes(message, offset)
        self._data["output_flags"], offset = structures.OutputFlags().from_bytes(
            message, offset
        )
        self._data["temperatures"], offset = structures.Temperatures().from_bytes(
            message, offset
        )
        self._data["tempCOSet"] = message[offset]
        self._data["statusCO"] = message[offset + 1]
        self._data["tempCWUSet"] = message[offset + 2]
        self._data["statusCWU"] = message[offset + 3]
        offset += 4
        self._data["alarms"], offset = structures.Alarms().from_bytes(message, offset)
        self._data["fuelLevel"] = message[offset]
        self._data["transmission"] = message[offset + 1]
        self._data["fanPower"] = util.unpack_float(message[offset + 2 : offset + 6])[0]
        self._data["boilerPower"] = message[offset + 6]
        self._data["boilerPowerKW"] = util.unpack_float(
            message[offset + 7 : offset + 11]
        )[0]
        self._data["fuelStream"] = util.unpack_float(
            message[offset + 11 : offset + 15]
        )[0]
        self._data["thermostat"] = message[offset + 15]
        offset += 16
        self._data["versions"], offset = structures.Versions().from_bytes(
            message, offset
        )
        self._data["lambda"], offset = structures.Lambda().from_bytes(message, offset)
        self._data["thermostats"], offset = structures.Thermostats().from_bytes(
            message, offset
        )
        self._data["mixers"], offset = structures.Mixers().from_bytes(message, offset)


class UID(Frame):
    """Contains device UID."""

    type_: int = 0xB9

    def parse_message(self, message: bytearray) -> None:
        """Parses UID message into usable data.

        Keywords arguments:
        message -- message to parse
        """
        self._data = {}
        offset = 0
        self._data["reg_type"] = message[offset]
        offset += 1
        self._data["reg_prod"] = util.unpack_ushort(message[offset : offset + 2])
        offset += 2
        self._data["UID"], offset = structures.UID().from_bytes(message, offset)
        self._data["reg_logo"] = util.unpack_ushort(message[offset : offset + 2])
        offset += 2
        self._data["reg_img"] = util.unpack_ushort(message[offset : offset + 2])
        offset += 2
        self._data["reg_name"] = structures.VarString().from_bytes(message, offset)


class Password(Frame):
    """Contains device service password."""

    type_: int = 0xBA

    def parse_message(self, message: bytearray) -> None:
        """Parses ProgramVersion message into usable data.

        Keywords arguments:
        message -- message to parse
        """
        password = message[1:]
        if password:
            self._data = password.decode()


class RegData(Frame):
    """Contains current regulator data."""

    type_: int = 0x08
    struct: list = []

    VERSION: str = "1.0"
    DATA_TYPES_LEN: list = [0, 1, 2, 4, 1, 2, 4, 4, 0, 8, 1, -1, -1, 8, 8, 4, 16]
    DATATYPE_UNDEFINED0: int = 0
    DATATYPE_SHORT_INT: int = 1
    DATATYPE_INT: int = 2
    DATATYPE_LONG_INT: int = 3
    DATATYPE_BYTE: int = 4
    DATATYPE_WORD: int = 5
    DATATYPE_DWORD: int = 6
    DATATYPE_SHORT_REAL: int = 7
    DATATYPE_UNDEVINED8: int = 8
    DATATYPE_LONG_REAL: int = 9
    DATATYPE_BOOLEAN: int = 10
    DATATYPE_BCD: int = 11
    DATATYPE_STRING: int = 12
    DATATYPE_INT_64: int = 13
    DATATYPE_UINT_64: int = 14
    DATATYPE_IPv4: int = 15
    DATATYPE_IPv6: int = 16

    def parse_message(self, message: bytearray) -> None:
        """Parses RegData message into usable data.

        Keywords arguments:
        message -- message to parse
        """
        offset = 2
        frame_version = f"{message[offset+1]}.{message[offset]}"
        offset += 2
        self._data = {}
        if frame_version == self.VERSION:
            (
                self._data["frame_versions"],
                offset,
            ) = structures.FrameVersions().from_bytes(message, offset)


class Timezones(Frame):
    """Contains device timezone info."""

    type_: int = 0xB6


class Parameters(Frame):
    """Contains editable parameters."""

    type_: int = 0xB1

    def parse_message(self, message: bytearray) -> None:
        """Parses Parameters message into usable data.

        Keywords arguments:
        message -- message to parse
        """
        first = message[1]
        offset = 3
        parameters_number = message[2]
        self._data = {}
        if parameters_number > 0:
            for parameter in range(first, parameters_number + first):
                if parameter < len(EDITABLE_PARAMS):
                    parameter_name = EDITABLE_PARAMS[parameter]
                    parameter_size = 1
                    value = util.unpack_ushort(
                        message[offset : offset + parameter_size]
                    )
                    min_ = util.unpack_ushort(
                        message[offset + parameter_size : offset + 2 * parameter_size]
                    )
                    max_ = util.unpack_ushort(
                        message[
                            offset + 2 * parameter_size : offset + 3 * parameter_size
                        ]
                    )
                    if util.check_parameter(
                        message[offset : offset + parameter_size * 3]
                    ):
                        self._data[parameter_name] = {
                            "value": value,
                            "min": min_,
                            "max": max_,
                        }

                    offset += parameter_size * 3


class MixerParameters(Frame):
    """Contains current mixers parameters."""

    type_: int = 0xD5


class DataStructure(Frame):
    """Contains device data structure."""

    type_: int = 0xD5

    def parse_message(self, message: bytearray) -> None:
        """Parses DataStructure message into usable data.

        Keywords arguments:
        message -- message to parse
        """
        offset = 0
        integrity_blocks_number = util.unpack_ushort(message[offset : offset + 2])
        offset += 2
        self._data = []
        if integrity_blocks_number > 0:
            for _ in range(integrity_blocks_number):
                param_type = message[offset]
                param_id = util.unpack_ushort(message[offset + 1 : offset + 3])
                self._data.append({"id": param_id, "type": param_type})
                offset += 3
