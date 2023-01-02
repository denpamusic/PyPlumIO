"""Contains network info structure decoder."""
from __future__ import annotations

from typing import Final, Optional, Tuple

from pyplumio import util
from pyplumio.helpers.network_info import (
    EthernetParameters,
    NetworkInfo,
    WirelessParameters,
)
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures import Structure, ensure_device_data

ATTR_NETWORK: Final = "network"


class NetworkInfoStructure(Structure):
    """Represents network info data structure."""

    def encode(self, data: DeviceDataType) -> bytearray:
        """Encode data and return bytearray."""
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

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
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

        return ensure_device_data(data, {ATTR_NETWORK: network_info}), offset
