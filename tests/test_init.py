"""Contains tests for init."""

from pyplumio import open_serial_connection, open_tcp_connection
from pyplumio.connection import SerialConnection, TcpConnection


def test_helper_methods() -> None:
    """Test open connection helpers."""
    serial_connection = open_serial_connection("/dev/ttyTEST0", baudrate=9600)
    assert isinstance(serial_connection, SerialConnection)
    assert serial_connection.device == "/dev/ttyTEST0"
    assert serial_connection.baudrate == 9600
    tcp_connection = open_tcp_connection("1.1.1.1", port=3939)
    assert isinstance(tcp_connection, TcpConnection)
    assert tcp_connection.host == "1.1.1.1"
    assert tcp_connection.port == 3939
