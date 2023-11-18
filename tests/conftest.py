"""Contains fixtures for the test suite."""

import asyncio
from unittest.mock import patch

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
