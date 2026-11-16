"""Contains shared fixtures and synthetic device definitions for CLI tests."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Final

import pytest

from pyplumio.cli.codegen import custom_module_path, generate_custom_parameter_module
from pyplumio.cli.state import AppState, AppStep
from pyplumio.const import ProductType
from pyplumio.parameters import ParameterValues
from pyplumio.parameters.custom import custom_parameters, number, switch
from pyplumio.structures.product_info import ProductInfo
from tests.conftest import DUMMY_MODEL

DUMMY_ID: Final = 999
DUMMY_SLUG: Final = "ecomax_999_test"
DUMMY_COMMENTS: Final[dict[int, str]] = {
    3: (
        "Long comment that wraps across multiple lines because it exceeds the "
        "seventy-eight character limit per comment line."
    ),
    4: "0 - pellets, 1 - wood",
}

DUMMY_PARAMETERS: Final = custom_parameters(
    model=DUMMY_MODEL,
    id=DUMMY_ID,
    patches={
        "summer_mode_disable_temp": number(
            "summer_mode_disable_temp",
            step=0.5,
            offset=-5,
            unit="°C",
        ),
    },
    service_parameters={
        0: number("max_boiler_power", unit="kW"),
        1: number("fan_power", unit="%"),
        2: number("feeder_coefficient", step=0.1, offset=5, unit="kg/h"),
        3: switch("fuzzy_logic", optimistic=True),
        4: number("fuel_type"),
    },
)


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
            DUMMY_PARAMETERS.service_parameters,
            DUMMY_PARAMETERS.patches,
            comments=comments,
        ),
        encoding="utf-8",
    )
    return module_path


__all__ = (
    "DUMMY_COMMENTS",
    "DUMMY_ID",
    "DUMMY_MODEL",
    "DUMMY_PARAMETERS",
    "DUMMY_SLUG",
    "app_step",
    "dummy_product_info",
    "dummy_service_parameters_frame",
    "product_info",
    "write_dummy_custom_module",
)
