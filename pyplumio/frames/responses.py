"""Contains response frame classes."""

import struct
from typing import Any, Dict, Final

from pyplumio import util
from pyplumio.constants import DATA_MODE
from pyplumio.data_types import DATA_TYPES
from pyplumio.helpers.network import Network
from pyplumio.structures import device_parameters, mixer_parameters, uid, var_string
from pyplumio.structures.outputs import OUTPUTS
from pyplumio.structures.statuses import HEATING_TARGET, WATER_HEATER_TARGET
from pyplumio.structures.temperatures import TEMPERATURES
from pyplumio.version import __version__

from . import Response


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

    def create_message(self) -> bytearray:
        """Creates DeviceAvailable message."""
        message = bytearray()
        message += b"\x01"
        if self._data is None:
            self._data = {}

        if "network" not in self._data:
            self._data["network"] = Network()

        network = self._data["network"]
        message += util.ip4_to_bytes(getattr(network.eth, "ip"))
        message += util.ip4_to_bytes(getattr(network.eth, "netmask"))
        message += util.ip4_to_bytes(getattr(network.eth, "gateway"))
        message.append(network.eth.status)
        message += util.ip4_to_bytes(getattr(network.wlan, "ip"))
        message += util.ip4_to_bytes(getattr(network.wlan, "netmask"))
        message += util.ip4_to_bytes(getattr(network.wlan, "gateway"))
        message.append(network.server_status)
        message.append(network.wlan.encryption)
        message.append(network.wlan.quality)
        message.append(network.wlan.status)
        message += b"\x00" * 4
        message.append(len(network.wlan.ssid))
        message += network.wlan.ssid.encode("utf-8")

        return message

    def parse_message(self, message: bytearray) -> None:
        """Parses DeviceAvailable message into usable data.

        Keywords arguments:
            message -- message to parse
        """
        offset = 1
        network = Network()
        network.eth.ip = util.ip4_from_bytes(message[offset : offset + 4])
        network.eth.netmask = util.ip4_from_bytes(message[offset + 4 : offset + 8])
        network.eth.gateway = util.ip4_from_bytes(message[offset + 8 : offset + 12])
        network.eth.status = bool(message[offset + 13])
        offset += 13
        network.wlan.ip = util.ip4_from_bytes(message[offset : offset + 4])
        network.wlan.netmask = util.ip4_from_bytes(message[offset + 4 : offset + 8])
        network.wlan.gateway = util.ip4_from_bytes(message[offset + 8 : offset + 12])
        network.server_status = bool(message[offset + 12])
        offset += 12
        network.wlan.encryption = int(message[offset + 1])
        network.wlan.quality = int(message[offset + 2])
        network.wlan.status = bool(message[offset + 3])
        offset += 8
        network.wlan.ssid = var_string.from_bytes(message, offset)[0]
        self._data["network"] = network


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


class BoilerParameters(Response):
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
        self._data, _ = mixer_parameters.from_bytes(message)


REGDATA_SCHEMA: Final = {
    1792: DATA_MODE,
    1024: TEMPERATURES[0],
    1026: TEMPERATURES[1],
    1025: TEMPERATURES[2],
    1027: TEMPERATURES[3],
    1030: TEMPERATURES[5],
    1280: HEATING_TARGET,
    1281: WATER_HEATER_TARGET,
    1536: OUTPUTS[0],
    1538: OUTPUTS[1],
    1541: OUTPUTS[2],
    1542: OUTPUTS[3],
    3: OUTPUTS[5],
}


class DataSchema(Response):
    """Contains device data structure.

    Attributes:
        type_ -- frame type
    """

    type_: int = 0xD5

    def parse_message(self, message: bytearray) -> None:
        """Parses DataSchema message into usable data.

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
                self._data.append((param_name, DATA_TYPES[param_type]()))
                offset += 3


class SetBoilerParameter(Response):
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
