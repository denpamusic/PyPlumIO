"""Contains ecoSTER device representation."""
from __future__ import annotations

from typing import ClassVar

from pyplumio.const import DeviceType
from pyplumio.devices import Addressable


class EcoSTER(Addressable):
    """Represents ecoSTER thermostat."""

    address: ClassVar[int] = DeviceType.ECOSTER
