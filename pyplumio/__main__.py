"""Contains a serial connection example."""

from __future__ import annotations

import asyncio

import pyplumio


async def main() -> None:
    """Connect and print out device sensors and parameters."""
    async with pyplumio.serial_for_url("/dev/ttyUSB0", baudrate=115200) as connection:
        device = await connection.get("ecomax")
        sensors = await device.get("sensors")
        parameters = await device.get("parameters")

    print(sensors)
    print(parameters)


asyncio.run(main())
