"""Contains serial connection example."""
from __future__ import annotations

import asyncio

from pyplumio import SerialConnection


async def main() -> None:
    """Connect and print out device sensors and parameters."""
    async with SerialConnection(device="/dev/ttyUSB0", baudrate=115200) as connection:
        await connection.connect()
        device = connection.wait_for_device("ecomax")
        sensors = await device.get_value("sensors")
        parameters = await device.get_value("parameters")

    print(sensors)
    print(parameters)


asyncio.run(main())
