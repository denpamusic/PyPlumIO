from pyplumio import econet_serial_connection, econet_tcp_connection
from pyplumio.econet import SerialConnection, TCPConnection


def test_econet_tcp_connection():
    econet = econet_tcp_connection("localhost", 8899)
    assert isinstance(econet, TCPConnection)


def test_econet_serial_connection():
    econet = econet_serial_connection("/dev/ttyUSB0")
    assert isinstance(econet, SerialConnection)
