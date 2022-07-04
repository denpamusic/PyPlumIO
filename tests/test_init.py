"""Contains tests for init."""

from pyplumio import (
    SerialConnection,
    TcpConnection,
    ethernet_parameters,
    open_serial_connection,
    open_tcp_connection,
    wireless_parameters,
)
from pyplumio.helpers.network_info import EthernetParameters


def test_connection_helpers() -> None:
    """Test open connection helpers."""
    serial_connection = open_serial_connection("/dev/ttyTEST0", baudrate=9600)
    assert isinstance(serial_connection, SerialConnection)
    assert serial_connection.device == "/dev/ttyTEST0"
    assert serial_connection.baudrate == 9600
    tcp_connection = open_tcp_connection("1.1.1.1", port=3939)
    assert isinstance(tcp_connection, TcpConnection)
    assert tcp_connection.host == "1.1.1.1"
    assert tcp_connection.port == 3939


def test_network_parameter_helpers() -> None:
    """Test network parameter helpers."""
    ethernet = ethernet_parameters(ip="1.1.1.2", gateway="1.1.1.1")
    assert isinstance(ethernet, EthernetParameters)
    assert ethernet.status
    assert ethernet.ip == "1.1.1.2"
    assert ethernet.gateway == "1.1.1.1"
    wireless = wireless_parameters(ssid="My SSID")
    assert wireless.status
    assert wireless.ssid == "My SSID"
