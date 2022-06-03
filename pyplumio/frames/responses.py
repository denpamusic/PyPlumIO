"""Contains response frame classes."""

import struct
from typing import Final

from pyplumio import util
from pyplumio.constants import DATA_MODE
from pyplumio.data_types import DATA_TYPES
from pyplumio.helpers.network_info import NetworkInfo
from pyplumio.helpers.product_info import ProductInfo
from pyplumio.helpers.version_info import VersionInfo
from pyplumio.structures import device_parameters, mixer_parameters, uid, var_string
from pyplumio.structures.outputs import OUTPUTS
from pyplumio.structures.statuses import HEATING_TARGET, WATER_HEATER_TARGET
from pyplumio.structures.temperatures import TEMPERATURES

from . import Response


class ProgramVersion(Response):
    """Contains information about device software and hardware version.

    Attributes:
        frame_type -- frame type
    """

    frame_type: int = 0xC0

    def create_message(self) -> bytearray:
        """Creates ProgramVersion message."""
        if self._data is None:
            self._data = {}

        if "version" not in self._data:
            self._data["version"] = VersionInfo()

        version_info = self._data["version"]
        message = bytearray(15)
        struct.pack_into(
            "<2sB2s3s3HB",
            message,
            0,
            version_info.struct_tag,
            version_info.struct_version,
            version_info.device_id,
            version_info.processor_signature,
            *(int(x) for x in version_info.software.split(".", 2)),
            self.sender,
        )

        return message

    def parse_message(self, message: bytearray):
        """Parses ProgramVersion message into usable data.

        Keywords arguments:
            message -- message to parse
        """
        version_info = VersionInfo()
        [
            version_info.struct_tag,
            version_info.struct_version,
            version_info.device_id,
            version_info.processor_signature,
            software_version,
            self.recipient,
        ] = struct.unpack_from("<2sB2s3s3sB", message)
        version_info.software = ".".join(str(x) for x in software_version)
        self._data["version"] = version_info


class DeviceAvailable(Response):
    """Contains device information.

    Attributes:
        frame_type -- frame type
    """

    frame_type: int = 0xB0

    def create_message(self) -> bytearray:
        """Creates DeviceAvailable message."""
        message = bytearray()
        message += b"\x01"
        if self._data is None:
            self._data = {}

        if "network" not in self._data:
            self._data["network"] = NetworkInfo()

        network_info = self._data["network"]
        message += util.ip4_to_bytes(network_info.eth.ip)
        message += util.ip4_to_bytes(network_info.eth.netmask)
        message += util.ip4_to_bytes(network_info.eth.gateway)
        message.append(network_info.eth.status)
        message += util.ip4_to_bytes(network_info.wlan.ip)
        message += util.ip4_to_bytes(network_info.wlan.netmask)
        message += util.ip4_to_bytes(network_info.wlan.gateway)
        message.append(network_info.server_status)
        message.append(network_info.wlan.encryption)
        message.append(network_info.wlan.quality)
        message.append(network_info.wlan.status)
        message += b"\x00" * 4
        message.append(len(network_info.wlan.ssid))
        message += network_info.wlan.ssid.encode("utf-8")

        return message

    def parse_message(self, message: bytearray) -> None:
        """Parses DeviceAvailable message into usable data.

        Keywords arguments:
            message -- message to parse
        """
        offset = 1
        network_info = NetworkInfo()
        network_info.eth.ip = util.ip4_from_bytes(message[offset : offset + 4])
        network_info.eth.netmask = util.ip4_from_bytes(message[offset + 4 : offset + 8])
        network_info.eth.gateway = util.ip4_from_bytes(
            message[offset + 8 : offset + 12]
        )
        network_info.eth.status = bool(message[offset + 13])
        offset += 13
        network_info.wlan.ip = util.ip4_from_bytes(message[offset : offset + 4])
        network_info.wlan.netmask = util.ip4_from_bytes(
            message[offset + 4 : offset + 8]
        )
        network_info.wlan.gateway = util.ip4_from_bytes(
            message[offset + 8 : offset + 12]
        )
        network_info.server_status = bool(message[offset + 12])
        offset += 12
        network_info.wlan.encryption = int(message[offset + 1])
        network_info.wlan.quality = int(message[offset + 2])
        network_info.wlan.status = bool(message[offset + 3])
        offset += 8
        network_info.wlan.ssid = var_string.from_bytes(message, offset)[0]
        self._data = {"network": network_info}


class UID(Response):
    """Contains device UID.

    Attributes:
        frame_type -- frame type
    """

    frame_type: int = 0xB9

    def parse_message(self, message: bytearray) -> None:
        """Parses UID message into usable data.

        Keywords arguments:
            message -- message to parse
        """

        product_info = ProductInfo()
        product_info.type, product_info.product = struct.unpack_from("<BH", message)
        product_info.uid, offset = uid.from_bytes(message, offset=3)
        product_info.logo, product_info.image = struct.unpack_from("<HH", message)
        product_info.model, _ = var_string.from_bytes(message, offset + 4)
        self._data = {"product": product_info}


class Password(Response):
    """Contains device service password.

    Attributes:
        frame_type -- frame type
    """

    frame_type: int = 0xBA

    def parse_message(self, message: bytearray) -> None:
        """Parses Password message into usable data.

        Keywords arguments:
            message -- message to parse
        """
        password = message[1:].decode() if message[1:] else None
        self._data = {"password": password}


class BoilerParameters(Response):
    """Contains editable parameters.

    Attributes:
        frame_type -- frame type
    """

    frame_type: int = 0xB1

    def parse_message(self, message: bytearray) -> None:
        """Parses Parameters message into usable data.

        Keywords arguments:
            message -- message to parse
        """
        self._data, _ = device_parameters.from_bytes(message)


class MixerParameters(Response):
    """Contains current mixers parameters.

    Attributes:
        frame_type -- frame type
    """

    frame_type: int = 0xB2

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
        frame_type -- frame type
    """

    frame_type: int = 0xD5

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
        frame_type -- frame type
    """

    frame_type: int = 0xB3


class SetMixerParameter(Response):
    """Sets mixer parameter.

    Attributes:
        frame_type -- frame type
    """

    frame_type: int = 0xB4


class BoilerControl(Response):
    """Contains boiler control response.

    Attributes:
        frame_type -- frame type
    """

    frame_type: int = 0xBB
