"""Contains serial connection example."""

import pyplumio
from pyplumio.connection import Connection
from pyplumio.devices import DevicesCollection


async def main(devices: DevicesCollection, connection: Connection) -> None:
    """This callback will be called every second.

    Keyword arguments:
        devices -- collection of all available devices
        connection -- instance of current connection
    """
    if devices.ecomax:
        print(devices.ecomax)


pyplumio.serial(main, device="/dev/ttyUSB0", baudrate=115200, interval=1)
