"""Fixtures for PyPlumIO test suite."""

from unittest.mock import patch

import pytest

from pyplumio.devices import ECOMAX_ADDRESS, DevicesCollection, EcoMAX
from pyplumio.mixers import Mixer
from pyplumio.storage import FrameBucket


@pytest.fixture(name="frame_bucket")
def fixture_frame_bucket() -> FrameBucket:
    """Return instance of frame version bucket."""
    return FrameBucket()


@pytest.fixture(name="ecomax")
def fixture_ecomax() -> EcoMAX:
    """Return instance of ecoMAX device class."""
    return EcoMAX()


@pytest.fixture(name="devices")
def fixture_devices() -> DevicesCollection:
    """Return instance of device collection."""
    devices = DevicesCollection()
    devices.get(ECOMAX_ADDRESS)
    return devices


@pytest.fixture(name="mixer")
def fixture_mixer() -> Mixer:
    """Return instance of mixer class."""
    return Mixer()


@pytest.fixture(name="bypass_asyncio_sleep")
def fixture_bypass_asyncio_sleep():
    """Bypass asyncio sleep."""
    with patch("asyncio.sleep"):
        yield


@pytest.fixture(name="bypass_asyncio_create_task")
def fixture_bypass_asyncio_create_task():
    """Bypass asyncio create task."""
    with patch("asyncio.create_task"):
        yield
