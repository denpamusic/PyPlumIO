"""Contains a network info structure decoder."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

from pyplumio.const import EncryptionType
from pyplumio.helpers.data_types import IPv4, VarString
from pyplumio.helpers.typing import EventDataType
from pyplumio.structures import Structure
from pyplumio.utils import ensure_dict

ATTR_NETWORK: Final = "network"

DEFAULT_IP: Final = "0.0.0.0"
DEFAULT_NETMASK: Final = "255.255.255.0"

NETWORK_INFO_SIZE: Final = 25


@dataclass
class EthernetParameters:
    """Represents an ethernet parameters."""

    #: IP address.
    ip: str = DEFAULT_IP

    #: IP subnet mask.
    netmask: str = DEFAULT_NETMASK

    #: Gateway IP address.
    gateway: str = DEFAULT_IP

    #: Connection status. Parameters will be ignored if set to False.
    status: bool = True


@dataclass
class WirelessParameters(EthernetParameters):
    """Represents a wireless network parameters."""

    #: Wireless Service Set IDentifier.
    ssid: str = ""

    #: Wireless encryption standard.
    encryption: EncryptionType = EncryptionType.NONE

    #: Wireless signal strength in percentage.
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
        message += IPv4(network_info.eth.ip).to_bytes()
        message += IPv4(network_info.eth.netmask).to_bytes()
        message += IPv4(network_info.eth.gateway).to_bytes()
        message.append(network_info.eth.status)
        message += IPv4(network_info.wlan.ip).to_bytes()
        message += IPv4(network_info.wlan.netmask).to_bytes()
        message += IPv4(network_info.wlan.gateway).to_bytes()
        message.append(network_info.server_status)
        message.append(network_info.wlan.encryption)
        message.append(network_info.wlan.signal_quality)
        message.append(network_info.wlan.status)
        message += b"\x00" * 4
        message += VarString(network_info.wlan.ssid).to_bytes()

        return message

    def decode(
        self, message: bytearray, offset: int = 0, data: EventDataType | None = None
    ) -> tuple[EventDataType, int]:
        """Decode bytes and return message data and offset."""
        return (
            ensure_dict(
                data,
                {
                    ATTR_NETWORK: NetworkInfo(
                        eth=EthernetParameters(
                            ip=IPv4.from_bytes(message, offset).value,
                            netmask=IPv4.from_bytes(message, offset + 4).value,
                            gateway=IPv4.from_bytes(message, offset + 8).value,
                            status=bool(message[offset + 13]),
                        ),
                        wlan=WirelessParameters(
                            ip=IPv4.from_bytes(message, offset + 13).value,
                            netmask=IPv4.from_bytes(message, offset + 17).value,
                            gateway=IPv4.from_bytes(message, offset + 21).value,
                            encryption=EncryptionType(int(message[offset + 26])),
                            signal_quality=int(message[offset + 27]),
                            status=bool(message[offset + 28]),
                            ssid=VarString.from_bytes(message, offset + 33).value,
                        ),
                        server_status=bool(message[offset + 25]),
                    )
                },
            ),
            offset + NETWORK_INFO_SIZE,
        )
