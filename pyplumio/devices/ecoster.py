"""Contains ecoSTER device representation."""
from __future__ import annotations

from typing import ClassVar

from pyplumio.devices import Device, DeviceTypes


class EcoSTER(Device):
    """Represents ecoSTER thermostat."""

    address: ClassVar[int] = DeviceTypes.ECOSTER
