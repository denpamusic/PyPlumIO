"""Contains serial connection example."""
from __future__ import annotations

import asyncio

import pyplumio


async def main() -> None:
    """Connect and print out device sensors and parameters."""
    async with pyplumio.serial("/dev/ttyUSB0", 115200) as connection:
        device = await connection.get_device("ecomax")
        sensors = await device.get("sensors")
        parameters = await device.get("parameters")

    print(sensors)
    print(parameters)


asyncio.run(main())
