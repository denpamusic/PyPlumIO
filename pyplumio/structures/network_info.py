"""Contains a network info structure decoder."""
from __future__ import annotations

from dataclasses import dataclass, field
import socket
from typing import Final

from pyplumio import util
from pyplumio.const import EncryptionType
from pyplumio.helpers.typing import EventDataType
from pyplumio.structures import Structure, ensure_device_data

ATTR_NETWORK: Final = "network"

DEFAULT_IP: Final = "0.0.0.0"
DEFAULT_NETMASK: Final = "255.255.255.0"


@dataclass
class EthernetParameters:
    """Represents an ethernet parameters."""

    ip: str = DEFAULT_IP
    netmask: str = DEFAULT_NETMASK
    gateway: str = DEFAULT_IP
    status: bool = False


@dataclass
class WirelessParameters(EthernetParameters):
    """Represents a wireless network parameters."""

    ssid: str = ""
    encryption: EncryptionType = EncryptionType.NONE
    signal_quality: int = 100


@dataclass
class NetworkInfo:
    """Represents a network parameters."""

    eth: EthernetParameters = field(default_factory=EthernetParameters)
    wlan: WirelessParameters = field(default_factory=WirelessParameters)
    server_status: bool = True


class NetworkInfoStructure(Structure):
    """Represents a network info data structure."""

    def encode(self, data: EventDataType) -> bytearray:
        """Encode data to the bytearray message."""
        message = bytearray()
        message += b"\x01"
        network_info = data[ATTR_NETWORK] if ATTR_NETWORK in data else NetworkInfo()
        message += socket.inet_aton(network_info.eth.ip)
        message += socket.inet_aton(network_info.eth.netmask)
        message += socket.inet_aton(network_info.eth.gateway)
        message.append(network_info.eth.status)
        message += socket.inet_aton(network_info.wlan.ip)
        message += socket.inet_aton(network_info.wlan.netmask)
        message += socket.inet_aton(network_info.wlan.gateway)
        message.append(network_info.server_status)
        message.append(network_info.wlan.encryption)
        message.append(network_info.wlan.signal_quality)
        message.append(network_info.wlan.status)
        message += b"\x00" * 4
        message.append(len(network_info.wlan.ssid))
        message += network_info.wlan.ssid.encode("utf-8")

        return message

    def decode(
        self, message: bytearray, offset: int = 0, data: EventDataType | None = None
    ) -> tuple[EventDataType, int]:
        """Decode bytes and return message data and offset."""
        return (
            ensure_device_data(
                data,
                {
                    ATTR_NETWORK: NetworkInfo(
                        eth=EthernetParameters(
                            ip=socket.inet_ntoa(message[offset : offset + 4]),
                            netmask=socket.inet_ntoa(message[offset + 4 : offset + 8]),
                            gateway=socket.inet_ntoa(message[offset + 8 : offset + 12]),
                            status=bool(message[offset + 13]),
                        ),
                        wlan=WirelessParameters(
                            ip=socket.inet_ntoa(message[offset + 13 : offset + 17]),
                            netmask=socket.inet_ntoa(
                                message[offset + 17 : offset + 21]
                            ),
                            gateway=socket.inet_ntoa(
                                message[offset + 21 : offset + 25]
                            ),
                            encryption=EncryptionType(int(message[offset + 26])),
                            signal_quality=int(message[offset + 27]),
                            status=bool(message[offset + 28]),
                            ssid=util.unpack_string(message, offset + 33),
                        ),
                        server_status=bool(message[offset + 25]),
                    )
                },
            ),
            offset + 25,
        )
