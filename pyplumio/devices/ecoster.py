"""Contains an ecoSTER class."""
from __future__ import annotations

from typing import ClassVar

from pyplumio.const import DeviceType
from pyplumio.devices import Addressable


class EcoSTER(Addressable):
    """Represents an ecoSTER thermostat."""

    address: ClassVar[int] = DeviceType.ECOSTER
