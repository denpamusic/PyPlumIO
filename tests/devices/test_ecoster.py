"""Contains tests for the ecoSTER device."""

import asyncio

from pyplumio.devices.ecoster import EcoSTER
from pyplumio.structures.network_info import NetworkInfo


def test_init() -> None:
    """Test ecoSTER instance."""
    ecoster = EcoSTER(asyncio.Queue(), network=NetworkInfo())
    assert isinstance(ecoster, EcoSTER)
