"""Contains ecoSTER device representation."""
from __future__ import annotations

from typing import ClassVar

from pyplumio.const import AddressTypes
from pyplumio.devices import Device


class EcoSTER(Device):
    """Represents ecoSTER thermostat."""

    address: ClassVar[int] = AddressTypes.ECOSTER
