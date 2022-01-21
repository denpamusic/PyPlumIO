"""Contains econet connection shortcut."""

from .econet import SerialConnection, TcpConnection
from .version import __version__  # noqa


def econet_tcp_connection(host: str, port: int, **kwargs):
    """Creates TCP connection instance.

    Keyword arguments:
    host -- serial device ip/hostname
    port -- serial device port
    **kwargs -- keyword arguments directly passed to asyncio's
        create_connection method
    """
    return TcpConnection(host, port, **kwargs)


def econet_serial_connection(device: str, baudrate: int = 115200, **kwargs):
    """Creates serial connection instance.

    Keyword arguments:
    device -- serial device url, e. g. /dev/ttyUSB0
    **kwargs -- keyword arguments directly passed to asyncio's
        create_connection method
    """
    return SerialConnection(device=device, baudrate=baudrate, **kwargs)
