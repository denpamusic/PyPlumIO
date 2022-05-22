"""Fixtures for PyPlumIO test suite."""

import pytest

from pyplumio.devices import ECOMAX_ADDRESS, DevicesCollection, EcoMAX
from pyplumio.mixers import Mixer
from pyplumio.storage import FrameBucket


@pytest.fixture(name="frame_bucket")
def fixture_frame_bucket() -> FrameBucket:
    return FrameBucket()


@pytest.fixture(name="ecomax")
def fixture_ecomax() -> EcoMAX:
    return EcoMAX()


@pytest.fixture(name="devices")
def fixture_devices() -> DevicesCollection:
    devices = DevicesCollection()
    devices.get(ECOMAX_ADDRESS)
    return devices


@pytest.fixture(name="mixer")
def fixture_mixer() -> Mixer:
    return Mixer()
