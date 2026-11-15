"""Contains shared fixtures and synthetic device definitions for CLI tests."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Final

import pytest

from pyplumio.cli.codegen import custom_module_path, generate_custom_parameter_module
from pyplumio.cli.state import AppState, AppStep
from pyplumio.const import PERCENTAGE, ProductType, UnitOfMeasurement
from pyplumio.parameters import ParameterValues
from pyplumio.parameters.custom import CustomParameters, ParameterOverride, Signature
from pyplumio.parameters.ecomax import EcomaxNumberDescription, EcomaxSwitchDescription
from pyplumio.structures.product_info import ProductInfo
from tests.conftest import DUMMY_MODEL

DUMMY_ID: Final = 999
DUMMY_SLUG: Final = "ecomax_999_test"
DUMMY_CLASS_NAME: Final = "EcoMAX999TEST"
DUMMY_COMMENTS: Final[dict[int, str]] = {
    3: (
        "Long comment that wraps across multiple lines because it exceeds the "
        "seventy-eight character limit per comment line."
    ),
    4: "0 - pellets, 1 - wood",
}


class EcoMAX999TEST(CustomParameters):
    """Custom parameters for ecoMAX 999-TEST."""

    __slots__ = ()

    signature = Signature(model=DUMMY_MODEL, id=DUMMY_ID)

    overrides = (
        ParameterOverride(
            original="summer_mode_disable_temp",
            replacement=EcomaxNumberDescription(
                name="summer_mode_disable_temp",
                step=0.5,
                offset=-5,
                unit_of_measurement=UnitOfMeasurement.CELSIUS,
            ),
        ),
    )

    descriptions = {
        0: EcomaxNumberDescription(
            name="max_boiler_power",
            unit_of_measurement=UnitOfMeasurement.KILO_WATT,
        ),
        1: EcomaxNumberDescription(
            name="fan_power",
            unit_of_measurement=PERCENTAGE,
        ),
        2: EcomaxNumberDescription(
            name="feeder_coefficient",
            step=0.1,
            offset=5,
            unit_of_measurement=UnitOfMeasurement.KILOGRAMS_PER_HOUR,
        ),
        3: EcomaxSwitchDescription(
            name="fuzzy_logic",
            optimistic=True,
        ),
        4: EcomaxNumberDescription(
            name="fuel_type",
        ),
    }


def app_step(state: AppState) -> AppStep:
    """Return app step without triggering mypy attribute narrowing."""
    return state.step


def dummy_product_info() -> ProductInfo:
    """Return synthetic product info for ecoMAX 999-TEST."""
    return ProductInfo(
        type=ProductType.ECOMAX_P,
        id=DUMMY_ID,
        uid="*TEST*",
        logo=0,
        image=0,
        model=DUMMY_MODEL,
    )


@pytest.fixture
def product_info() -> ProductInfo:
    """Return synthetic product info fixture for CLI tests."""
    return dummy_product_info()


def dummy_service_parameters_frame() -> tuple[bytes, list[tuple[int, ParameterValues]]]:
    """Build synthetic service parameters frame bytes and decoded entries."""
    entries: list[tuple[int, ParameterValues]] = [
        (0, ParameterValues(value=16, min_value=8, max_value=24)),
        (1, ParameterValues(value=50, min_value=20, max_value=100)),
        (2, ParameterValues(value=15, min_value=5, max_value=50)),
        (3, ParameterValues(value=1, min_value=0, max_value=1)),
        (4, ParameterValues(value=0, min_value=0, max_value=1)),
        (5, ParameterValues(value=42, min_value=0, max_value=100)),
    ]
    payload = bytearray([len(entries), 0])
    for _, values in entries:
        payload.extend((values.value, values.min_value, values.max_value))

    return bytes(payload), entries


def write_dummy_custom_module(
    root: Path,
    comments: Mapping[int, str] | None = DUMMY_COMMENTS,
) -> Path:
    """Write synthetic ecoMAX 999-TEST custom parameter module under root."""
    module_path = custom_module_path(root, DUMMY_SLUG)
    module_path.parent.mkdir(parents=True, exist_ok=True)
    module_path.write_text(
        generate_custom_parameter_module(
            dummy_product_info(),
            EcoMAX999TEST.descriptions,
            EcoMAX999TEST.overrides,
            comments=comments,
        ),
        encoding="utf-8",
    )
    return module_path


__all__ = (
    "DUMMY_CLASS_NAME",
    "DUMMY_COMMENTS",
    "DUMMY_ID",
    "DUMMY_MODEL",
    "DUMMY_SLUG",
    "EcoMAX999TEST",
    "app_step",
    "dummy_product_info",
    "dummy_service_parameters_frame",
    "product_info",
    "write_dummy_custom_module",
)
