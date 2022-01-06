from .constants import VERSION
from .econet import EcoNet

__version__ = VERSION

def econet_connection(host: str, port: int, **kwargs):
    return EcoNet(host, port, **kwargs)
