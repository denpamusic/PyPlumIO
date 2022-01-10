"""Contains econet connection shortcut."""

from .econet import EcoNET
from .version import __version__  # noqa


def econet_connection(host: str, port: int, **kwargs):
    """Creates ecoNET connection instance.

    Keyword arguments:
    host -- hostname or ip of rs485 to tcp bridge,
        connected to ecoMAX controller
    port -- port of rs485 to tcp bridge,
        connected to ecoMAX controller
    **kwargs -- keyword arguments directly passed to asyncio's
        create_connection method
    """
    return EcoNET(host, port, **kwargs)
