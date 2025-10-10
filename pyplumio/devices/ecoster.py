"""Contains an ecoSTER class."""

from __future__ import annotations

from pyplumio.const import DeviceType
from pyplumio.devices import PhysicalDevice, device_handler


@device_handler(DeviceType.ECOSTER)
class EcoSTER(PhysicalDevice):
    """Represents an ecoSTER thermostat."""

    __slots__ = ()


__all__ = ["EcoSTER"]
