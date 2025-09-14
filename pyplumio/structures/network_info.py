"""Contains a network info structure decoder."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Final

from pyplumio.const import EncryptionType
from pyplumio.data_types import IPv4, VarString
from pyplumio.structures import Structure
from pyplumio.utils import ensure_dict

ATTR_NETWORK: Final = "network"

DEFAULT_IP: Final = "0.0.0.0"
DEFAULT_NETMASK: Final = "255.255.255.0"

NETWORK_INFO_SIZE: Final = 25


@dataclass(frozen=True, slots=True, kw_only=True)
class EthernetParameters:
    """Represents an ethernet parameters."""

    #: IP address
    ip: str = DEFAULT_IP

    #: IP subnet mask
    netmask: str = DEFAULT_NETMASK

    #: Gateway IP address
    gateway: str = DEFAULT_IP

    #: Connection status. Parameters will be ignored if set to `False`
    status: bool = True


@dataclass(frozen=True, slots=True, kw_only=True)
class WirelessParameters(EthernetParameters):
    """Represents a wireless network parameters."""

    #: Wireless Service Set IDentifier
    ssid: str = ""

    #: Wireless encryption standard
    #: (0 - unknown, 1 - no encryption, 2 - WEP, 3 - WPA, 4 - WPA2)
    encryption: EncryptionType = EncryptionType.NONE

    #: Wireless signal strength in percentage
    signal_quality: int = 100


@dataclass(frozen=True, slots=True, kw_only=True)
class NetworkInfo:
    """Represents a network parameters."""

    eth: EthernetParameters = field(default_factory=EthernetParameters)
    wlan: WirelessParameters = field(default_factory=WirelessParameters)
    server_status: bool = True


class NetworkInfoStructure(Structure):
    """Represents a network info data structure."""

    __slots__ = ()

    def encode(self, data: dict[str, Any]) -> bytearray:
        """Encode data to the bytearray message."""
        network_info: NetworkInfo = data.get(ATTR_NETWORK, NetworkInfo())
        return bytearray(
            b"\1"
            + IPv4(network_info.eth.ip).to_bytes()
            + IPv4(network_info.eth.netmask).to_bytes()
            + IPv4(network_info.eth.gateway).to_bytes()
            + network_info.eth.status.to_bytes(length=1, byteorder="little")
            + IPv4(network_info.wlan.ip).to_bytes()
            + IPv4(network_info.wlan.netmask).to_bytes()
            + IPv4(network_info.wlan.gateway).to_bytes()
            + network_info.server_status.to_bytes(length=1, byteorder="little")
            + network_info.wlan.encryption.to_bytes(length=1, byteorder="little")
            + network_info.wlan.signal_quality.to_bytes(length=1, byteorder="little")
            + network_info.wlan.status.to_bytes(length=1, byteorder="little")
            + b"\0" * 4
            + VarString(network_info.wlan.ssid).to_bytes()
        )

    def decode(
        self, message: bytearray, offset: int = 0, data: dict[str, Any] | None = None
    ) -> tuple[dict[str, Any], int]:
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


__all__ = [
    "EthernetParameters",
    "WirelessParameters",
    "NetworkInfo",
    "NetworkInfoStructure",
    "ATTR_NETWORK",
    "DEFAULT_IP",
    "DEFAULT_NETMASK",
]
