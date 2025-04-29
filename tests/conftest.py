"""Contains fixtures for the test suite."""

import asyncio
from unittest.mock import patch

from freezegun import freeze_time
import pytest

from pyplumio.const import ProductType
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.structures.network_info import NetworkInfo
from pyplumio.structures.product_info import ATTR_PRODUCT, ProductInfo


@pytest.fixture(name="ecomax")
def fixture_ecomax() -> EcoMAX:
    """Return an ecoMAX object."""
    ecomax = EcoMAX(asyncio.Queue(), network=NetworkInfo())
    ecomax.data[ATTR_PRODUCT] = ProductInfo(
        type=ProductType.ECOMAX_P,
        id=90,
        uid="TEST",
        logo=23040,
        image=2816,
        model="ecoMAX 350P2-ZF",
    )
    return ecomax


@pytest.fixture(autouse=True)
def bypass_asyncio_sleep():
    """Bypass an asyncio sleep."""
    with patch("asyncio.sleep"):
        yield


@pytest.fixture(name="frozen_time")
def fixture_frozen_time():
    """Get frozen time."""
    with freeze_time("2012-12-12 12:00:00") as frozen_time:
        yield frozen_time
