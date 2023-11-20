"""Contains an ecoSTER class."""
from __future__ import annotations

from typing import ClassVar

from pyplumio.const import DeviceType
from pyplumio.devices import AddressableDevice


class EcoSTER(AddressableDevice):
    """Represents an ecoSTER thermostat."""

    address: ClassVar[int] = DeviceType.ECOSTER
