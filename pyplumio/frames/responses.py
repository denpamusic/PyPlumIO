"""Contains response frame classes."""

import struct

from pyplumio import util
from pyplumio.constants import (
    DATA_FAN_POWER,
    DATA_FUEL_CONSUMPTION,
    DATA_FUEL_LEVEL,
    DATA_LOAD,
    DATA_MODE,
    DATA_POWER,
    DATA_THERMOSTAT,
    DATA_TRANSMISSION,
    DEFAULT_IP,
    DEFAULT_NETMASK,
    EDITABLE_PARAMS,
    WLAN_ENCRYPTION,
    WLAN_ENCRYPTION_NONE,
)
from pyplumio.frame import Response
from pyplumio.structures import (
    alarms,
    frame_versions,
    lambda_,
    mixers,
    modules,
    output_flags,
    outputs,
    statuses,
    temperatures,
    thermostats,
    uid,
    var_string,
)
from pyplumio.version import __version__


class ProgramVersion(Response):
    """Contains information about device software and hardware version."""

    type_: int = 0xC0

    _defaults: dict = {
        "version": __version__,
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
            "<2sB2s3sHHHB",
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
        ] = struct.unpack_from("<2sB2s3sHHHB", message)
        self._data["version"] = ".".join(map(str, [version1, version2, version3]))


class DeviceAvailable(Response):
    """Contains ecoNET device information."""

    type_: int = 0xB0

    _defaults: dict = {
        "eth": {
            "ip": DEFAULT_IP,
            "netmask": DEFAULT_NETMASK,
            "gateway": DEFAULT_IP,
            "status": False,
        },
        "wlan": {
            "ip": DEFAULT_IP,
            "netmask": DEFAULT_NETMASK,
            "gateway": DEFAULT_IP,
            "status": False,
            "encryption": WLAN_ENCRYPTION[WLAN_ENCRYPTION_NONE],
            "quality": 100,
            "ssid": "",
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

        message.append(server["status"])
        message.append(wlan["encryption"])
        message.append(wlan["quality"])
        message.append(wlan["status"])

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

        self._data["server"]["status"] = bool(message[offset])
        self._data["wlan"]["encryption"] = int(message[offset + 1])
        self._data["wlan"]["quality"] = int(message[offset + 2])
        self._data["wlan"]["status"] = bool(message[offset + 3])
        offset += 8
        self._data["wlan"]["ssid"] = var_string.from_bytes(message, offset)


class CurrentData(Response):
    """Contains current device state data."""

    type_: int = 0x35

    def parse_message(self, message: bytearray) -> None:
        """Parses CurrentData message into usable data.

        Keywords arguments:
        message -- message to parse
        """
        self._data = {}
        offset = 0
        _, offset = frame_versions.from_bytes(message, offset, self._data)
        self._data[DATA_MODE] = message[offset]
        offset += 1
        _, offset = outputs.from_bytes(message, offset, self._data)
        _, offset = output_flags.from_bytes(message, offset, self._data)
        _, offset = temperatures.from_bytes(message, offset, self._data)
        _, offset = statuses.from_bytes(message, offset, self._data)
        _, offset = alarms.from_bytes(message, offset, self._data)
        self._data[DATA_FUEL_LEVEL] = message[offset]
        self._data[DATA_TRANSMISSION] = message[offset + 1]
        self._data[DATA_FAN_POWER] = util.unpack_float(
            message[offset + 2 : offset + 6]
        )[0]
        self._data[DATA_LOAD] = message[offset + 6]
        self._data[DATA_POWER] = util.unpack_float(message[offset + 7 : offset + 11])[0]
        self._data[DATA_FUEL_CONSUMPTION] = util.unpack_float(
            message[offset + 11 : offset + 15]
        )[0]
        self._data[DATA_THERMOSTAT] = message[offset + 15]
        offset += 16
        _, offset = modules.from_bytes(message, offset, self._data)
        _, offset = lambda_.from_bytes(message, offset, self._data)
        _, offset = thermostats.from_bytes(message, offset, self._data)
        _, offset = mixers.from_bytes(message, offset, self._data)


class UID(Response):
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
        self._data["UID"], offset = uid.from_bytes(message, offset)
        self._data["reg_logo"] = util.unpack_ushort(message[offset : offset + 2])
        offset += 2
        self._data["reg_img"] = util.unpack_ushort(message[offset : offset + 2])
        offset += 2
        self._data["reg_name"] = var_string.from_bytes(message, offset)


class Password(Response):
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


class RegData(Response):
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
            frame_versions.from_bytes(message, offset, self._data)


class Timezones(Response):
    """Contains device timezone info."""

    type_: int = 0xB6


class Parameters(Response):
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


class MixerParameters(Response):
    """Contains current mixers parameters."""

    type_: int = 0xB2


class DataStructure(Response):
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


class SetParameter(Response):
    """Contains set parameter response."""

    type_: int = 0xB3


class BoilerControl(Response):
    """Contains boiler control response."""

    type_: int = 0xBB
