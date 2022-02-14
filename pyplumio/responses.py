"""Contains response frame classes."""

import struct
from typing import Any, Dict

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
    DATA_TYPES,
    DEFAULT_IP,
    DEFAULT_NETMASK,
    REGDATA_SCHEMA,
    WLAN_ENCRYPTION,
    WLAN_ENCRYPTION_NONE,
)
from pyplumio.data_types import Boolean
from pyplumio.frame import Response
from pyplumio.structures import (
    alarms,
    device_parameters,
    frame_versions,
    lambda_,
    mixer_parameter,
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
    """Contains information about device software and hardware version.

    Attributes:
        type_ -- frame type
    """

    type_: int = 0xC0

    _defaults: Dict[str, Any] = {
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
    """Contains device information.

    Attributes:
        type_ -- frame type
    """

    type_: int = 0xB0

    _defaults: Dict[str, Dict[str, Any]] = {
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
        """Creates DeviceAvailable message."""
        message = bytearray()
        message += b"\x01"
        data = util.merge(self._defaults, self._data)
        eth = data["eth"]
        wlan = data["wlan"]
        server = data["server"]
        for address in ("ip", "netmask", "gateway"):
            message += util.ip4_to_bytes(eth[address])

        message.append(eth["status"])
        for address in ("ip", "netmask", "gateway"):
            message += util.ip4_to_bytes(wlan[address])

        message.append(server["status"])
        message.append(wlan["encryption"])
        message.append(wlan["quality"])
        message.append(wlan["status"])

        message += b"\x00" * 4
        message.append(len(wlan["ssid"]))
        message += wlan["ssid"].encode("utf-8")

        return message

    def parse_message(self, message: bytearray) -> None:
        """Parses DeviceAvailable message into usable data.

        Keywords arguments:
            message -- message to parse
        """
        self._data = {"eth": {}, "wlan": {}, "server": {}}
        offset = 1
        for part in ("ip", "netmask", "gateway"):
            self._data["eth"][part] = util.ip4_from_bytes(message[offset : offset + 4])
            offset += 4

        self._data["eth"]["status"] = bool(message[offset])
        offset += 1
        for part in ("ip", "netmask", "gateway"):
            self._data["wlan"][part] = util.ip4_from_bytes(message[offset : offset + 4])
            offset += 4

        self._data["server"]["status"] = bool(message[offset])
        self._data["wlan"]["encryption"] = int(message[offset + 1])
        self._data["wlan"]["quality"] = int(message[offset + 2])
        self._data["wlan"]["status"] = bool(message[offset + 3])
        offset += 8
        self._data["wlan"]["ssid"] = var_string.from_bytes(message, offset)


class RegData(Response):
    """Contains current regulator data.

    Attributes:
        type_ -- frame type
    """

    type_: int = 0x08

    VERSION: str = "1.0"

    def __init__(self, *args, **kwargs):
        """Creates new RegData frame object.

        Keyword arguments:
            *args -- arguments for parent class init
            **kwargs -- keyword arguments for parent class init
        """
        super().__init__(*args, **kwargs)
        self.struct = []

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
            _, offset = frame_versions.from_bytes(message, offset, self._data)
            boolean_index = 0
            for param in self.struct:
                param_id, param_type = param
                param_type.unpack(message[offset:])
                if isinstance(param_type, Boolean):
                    boolean_index = param_type.index(boolean_index)

                self._data[param_id] = param_type.value
                offset += param_type.size


class CurrentData(Response):
    """Contains current device state data.

    Attributes:
        type_ -- frame type
    """

    type_: int = 0x35

    def __init__(self, *args, **kwargs):
        """Creates new CurrentData frame object.

        Keyword arguments:
            *args -- arguments for parent class init
            **kwargs -- keyword arguments for parent class init
        """
        super().__init__(*args, **kwargs)
        self.struct = []

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
    """Contains device UID.

    Attributes:
        type_ -- frame type
    """

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
        self._data["reg_name"], offset = var_string.from_bytes(message, offset)


class Password(Response):
    """Contains device service password.

    Attributes:
        type_ -- frame type
    """

    type_: int = 0xBA

    def parse_message(self, message: bytearray) -> None:
        """Parses Password message into usable data.

        Keywords arguments:
            message -- message to parse
        """
        password = message[1:]
        if password:
            self._data = password.decode()


class Parameters(Response):
    """Contains editable parameters.

    Attributes:
        type_ -- frame type
    """

    type_: int = 0xB1

    def parse_message(self, message: bytearray) -> None:
        """Parses Parameters message into usable data.

        Keywords arguments:
            message -- message to parse
        """
        self._data, _ = device_parameters.from_bytes(message)


class MixerParameters(Response):
    """Contains current mixers parameters.

    Attributes:
        type_ -- frame type
    """

    type_: int = 0xB2

    def parse_message(self, message: bytearray) -> None:
        """Parses Parameters message into usable data.

        Keywords arguments:
        message -- message to parse
        """
        self._data, _ = mixer_parameter.from_bytes(message)


class DataStructure(Response):
    """Contains device data structure.

    Attributes:
        type_ -- frame type
    """

    type_: int = 0xD5

    def parse_message(self, message: bytearray) -> None:
        """Parses DataStructure message into usable data.

        Keywords arguments:
        message -- message to parse
        """
        offset = 0
        blocks_number = util.unpack_ushort(message[offset : offset + 2])
        offset += 2
        self._data = []
        if blocks_number > 0:
            for _ in range(blocks_number):
                param_type = message[offset]
                param_id = util.unpack_ushort(message[offset + 1 : offset + 3])
                param_name = REGDATA_SCHEMA.get(param_id, param_id)
                self._data.append([param_name, DATA_TYPES[param_type]()])
                offset += 3


class SetParameter(Response):
    """Contains set parameter response.

    Attributes:
        type_ -- frame type
    """

    type_: int = 0xB3


class SetMixerParameter(Response):
    """Sets mixer parameter.

    Attributes:
        type_ -- frame type
    """

    type_: int = 0xB4


class BoilerControl(Response):
    """Contains boiler control response.

    Attributes:
        type_ -- frame type
    """

    type_: int = 0xBB
