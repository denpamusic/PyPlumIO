from .constants import VERSION
from .econet import EcoNET

__version__ = VERSION

def econet_connection(host: str, port: int, **kwargs):
    return EcoNET(host, port, **kwargs)
