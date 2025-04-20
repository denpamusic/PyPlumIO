"""Contains an ecoSTER class."""

from __future__ import annotations

from pyplumio.const import DeviceType
from pyplumio.devices import PhysicalDevice


class EcoSTER(PhysicalDevice):
    """Represents an ecoSTER thermostat."""

    __slots__ = ()

    address = DeviceType.ECOSTER


__all__ = ["EcoSTER"]
