"""Contains module version data and econet connection shortcut."""

from .constants import VERSION
from .econet import EcoNET

__version__ = VERSION


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
