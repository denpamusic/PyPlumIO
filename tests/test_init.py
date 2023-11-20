"""Contains tests for the init module."""

from typing import Final

from pyplumio import (
    SerialConnection,
    TcpConnection,
    open_serial_connection,
    open_tcp_connection,
)

DEVICE: Final = "/dev/ttyUSB0"
IP: Final = "1.1.1.1"


def test_connection_helpers() -> None:
    """Test open connection helpers."""
    serial_connection = open_serial_connection(DEVICE, baudrate=9600)
    assert isinstance(serial_connection, SerialConnection)
    assert serial_connection.device == DEVICE
    assert serial_connection.baudrate == 9600
    tcp_connection = open_tcp_connection(IP, port=3939)
    assert isinstance(tcp_connection, TcpConnection)
    assert tcp_connection.host == IP
    assert tcp_connection.port == 3939
