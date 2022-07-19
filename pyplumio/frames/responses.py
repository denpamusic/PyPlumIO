"""Contains response frames."""
from __future__ import annotations

import struct
from typing import ClassVar, Dict, List, Tuple

from pyplumio import util
from pyplumio.const import (
    ATTR_MODE,
    ATTR_NETWORK,
    ATTR_PASSWORD,
    ATTR_PRODUCT,
    ATTR_SCHEMA,
    ATTR_VERSION,
)
from pyplumio.frames import Response, ResponseTypes
from pyplumio.helpers.data_types import DATA_TYPES, DataType
from pyplumio.helpers.network_info import (
    EthernetParameters,
    NetworkInfo,
    WirelessParameters,
)
from pyplumio.helpers.product_info import ProductInfo
from pyplumio.helpers.typing import DeviceDataType, MessageType
from pyplumio.helpers.version_info import VersionInfo
from pyplumio.structures import boiler_parameters, mixer_parameters, uid
from pyplumio.structures.outputs import (
    FAN_OUTPUT,
    FEEDER_OUTPUT,
    HEATING_PUMP_OUTPUT,
    LIGHTER_OUTPUT,
    WATER_HEATER_PUMP_OUTPUT,
)
from pyplumio.structures.statuses import HEATING_TARGET, WATER_HEATER_TARGET
from pyplumio.structures.temperatures import (
    EXHAUST_TEMP,
    FEEDER_TEMP,
    HEATING_TEMP,
    OUTSIDE_TEMP,
    WATER_HEATER_TEMP,
)


class ProgramVersion(Response):
    """Represents program version response. Contains software
    version info.
    """

    frame_type: ClassVar[int] = ResponseTypes.PROGRAM_VERSION

    def create_message(self, data: DeviceDataType) -> MessageType:
        """Create frame message."""
        message = bytearray(15)
        version_info = data[ATTR_VERSION] if ATTR_VERSION in data else VersionInfo()
        struct.pack_into(
            "<2sB2s3s3HB",
            message,
            0,
            version_info.struct_tag,
            version_info.struct_version,
            version_info.device_id,
            version_info.processor_signature,
            *map(int, version_info.software.split(".", 2)),
            self.sender,
        )
        return message

    def parse_message(self, message: MessageType) -> DeviceDataType:
        """Parse frame message."""
        version_info = VersionInfo()
        [
            version_info.struct_tag,
            version_info.struct_version,
            version_info.device_id,
            version_info.processor_signature,
            software_version1,
            software_version2,
            software_version3,
            self.recipient,
        ] = struct.unpack_from("<2sB2s3s3HB", message)
        version_info.software = ".".join(
            map(str, [software_version1, software_version2, software_version3])
        )
        return {ATTR_VERSION: version_info}


class DeviceAvailable(Response):
    """Represents device available response. Contains network
    information and status.
    """

    frame_type: ClassVar[int] = ResponseTypes.DEVICE_AVAILABLE

    def create_message(self, data: DeviceDataType) -> MessageType:
        """Creates frame message."""
        message = bytearray()
        message += b"\x01"
        network_info = data[ATTR_NETWORK] if ATTR_NETWORK in data else NetworkInfo()
        message += util.ip4_to_bytes(network_info.eth.ip)
        message += util.ip4_to_bytes(network_info.eth.netmask)
        message += util.ip4_to_bytes(network_info.eth.gateway)
        message.append(network_info.eth.status)
        message += util.ip4_to_bytes(network_info.wlan.ip)
        message += util.ip4_to_bytes(network_info.wlan.netmask)
        message += util.ip4_to_bytes(network_info.wlan.gateway)
        message.append(network_info.server_status)
        message.append(network_info.wlan.encryption)
        message.append(network_info.wlan.signal_quality)
        message.append(network_info.wlan.status)
        message += b"\x00" * 4
        message.append(len(network_info.wlan.ssid))
        message += network_info.wlan.ssid.encode("utf-8")
        return message

    def parse_message(self, message: MessageType) -> DeviceDataType:
        """Parse frame message."""
        offset = 1
        network_info = NetworkInfo(
            eth=EthernetParameters(
                ip=util.ip4_from_bytes(message[offset : offset + 4]),
                netmask=util.ip4_from_bytes(message[offset + 4 : offset + 8]),
                gateway=util.ip4_from_bytes(message[offset + 8 : offset + 12]),
                status=bool(message[offset + 13]),
            ),
            wlan=WirelessParameters(
                ip=util.ip4_from_bytes(message[offset + 13 : offset + 17]),
                netmask=util.ip4_from_bytes(message[offset + 17 : offset + 21]),
                gateway=util.ip4_from_bytes(message[offset + 21 : offset + 25]),
                encryption=int(message[offset + 26]),
                signal_quality=int(message[offset + 27]),
                status=bool(message[offset + 28]),
                ssid=util.unpack_string(message, offset + 33),
            ),
            server_status=bool(message[offset + 25]),
        )
        return {ATTR_NETWORK: network_info}


class UID(Response):
    """Represents UID response. Contains product and model info."""

    frame_type: ClassVar[int] = ResponseTypes.UID

    def parse_message(self, message: MessageType) -> DeviceDataType:
        """Parse frame message."""
        product_info = ProductInfo()
        product_info.type, product_info.product = struct.unpack_from("<BH", message)
        product_info.uid, offset = uid.from_bytes(message, offset=3)
        product_info.logo, product_info.image = struct.unpack_from("<HH", message)
        product_info.model = util.unpack_string(message, offset + 4)
        return {ATTR_PRODUCT: product_info}


class Password(Response):
    """Represent password response. Contains device service password."""

    frame_type: ClassVar[int] = ResponseTypes.PASSWORD

    def parse_message(self, message: MessageType) -> DeviceDataType:
        """Parse frame message."""
        password = message[1:].decode() if message[1:] else None
        return {ATTR_PASSWORD: password}


class BoilerParameters(Response):
    """Represents boiler parameters response. Contains editable boiler
    parameters.
    """

    frame_type: ClassVar[int] = ResponseTypes.BOILER_PARAMETERS

    def parse_message(self, message: MessageType) -> DeviceDataType:
        """Parse frame message."""
        return boiler_parameters.from_bytes(message)[0]


class MixerParameters(Response):
    """Represents mixer parameters response. Contains editable mixer
    parameters.
    """

    frame_type: ClassVar[int] = ResponseTypes.MIXER_PARAMETERS

    def parse_message(self, message: MessageType) -> DeviceDataType:
        """Parse frame message."""
        return mixer_parameters.from_bytes(message)[0]


REGATTR_SCHEMA: Dict[int, str] = {
    1792: ATTR_MODE,
    1024: HEATING_TEMP,
    1026: FEEDER_TEMP,
    1025: WATER_HEATER_TEMP,
    1027: OUTSIDE_TEMP,
    1030: EXHAUST_TEMP,
    1280: HEATING_TARGET,
    1281: WATER_HEATER_TARGET,
    1536: FAN_OUTPUT,
    1538: FEEDER_OUTPUT,
    1541: HEATING_PUMP_OUTPUT,
    1542: WATER_HEATER_PUMP_OUTPUT,
    3: LIGHTER_OUTPUT,
}


class DataSchema(Response):
    """Represents data schema response. Contains schema that describes
    regdata message structure.
    """

    frame_type: ClassVar[int] = ResponseTypes.DATA_SCHEMA

    def parse_message(self, message: MessageType) -> DeviceDataType:
        """Parse frame message."""
        offset = 0
        blocks_number = util.unpack_ushort(message[offset : offset + 2])
        offset += 2
        schema: List[Tuple[str, DataType]] = []
        if blocks_number > 0:
            for _ in range(blocks_number):
                param_type = message[offset]
                param_id = util.unpack_ushort(message[offset + 1 : offset + 3])
                param_name = REGATTR_SCHEMA.get(param_id, str(param_id))
                schema.append((param_name, DATA_TYPES[param_type]()))
                offset += 3

        return {ATTR_SCHEMA: schema}


class SetBoilerParameter(Response):
    """Represents set boiler parameter response. Empty response
    that aknowledges, that boiler parameter was successfully changed.
    """

    frame_type: ClassVar[int] = ResponseTypes.SET_BOILER_PARAMETER


class SetMixerParameter(Response):
    """Represents set mixer parameter response. Empty response
    that aknowledges, that mixer parameter was successfully changed.
    """

    frame_type: ClassVar[int] = ResponseTypes.SET_MIXER_PARAMETER


class BoilerControl(Response):
    """Represents boiler control response. Empty response
    that aknowledges, that boiler control request was successfully
    processed.
    """

    frame_type: ClassVar[int] = ResponseTypes.BOILER_CONTROL
