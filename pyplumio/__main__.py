"""Contains serial connection example."""

import pyplumio
from pyplumio.devices import DevicesCollection
from pyplumio.econet import EcoNET


async def main(devices: DevicesCollection, econet: EcoNET) -> None:
    """This callback will be called every second.

    Keyword arguments:
    devices -- contains all devices found on rs485 network
    econet -- instance of econet connection
    """
    if devices.ecomax:
        print(devices.ecomax)


pyplumio.serial(main, device="/dev/ttyUSB0", baudrate=115200, interval=1)
