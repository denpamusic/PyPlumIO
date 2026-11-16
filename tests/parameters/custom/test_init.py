"""Contains tests for the custom parameter descriptors."""

from __future__ import annotations

from pathlib import Path
import pkgutil
from types import ModuleType
from unittest.mock import patch

import pytest

from pyplumio.const import PERCENTAGE, ProductType, UnitOfMeasurement
import pyplumio.parameters.custom as custom_pkg
from pyplumio.parameters.custom import (
    CustomParameters,
    apply_custom_parameter_patches,
    custom_parameters,
    extract_custom_parameters,
    get_custom_service_parameter_types,
    load_custom_parameters,
    model_slug,
    number,
    switch,
)
from pyplumio.parameters.ecomax import (
    PARAMETER_TYPES as ECOMAX_PARAMETER_TYPES,
    EcomaxNumberDescription,
    EcomaxSwitchDescription,
)
from pyplumio.structures.product_info import ProductInfo
from pyplumio.utils import import_module
from tests.conftest import DUMMY_MODEL

TESTS_ROOT = Path(__file__).resolve().parents[2]
CUSTOM_MODULE_NAMES = sorted(
    name for _, name, _ in pkgutil.iter_modules(custom_pkg.__path__)
)

DUMMY_PARAMETERS = custom_parameters(
    model=DUMMY_MODEL,
    id=1,
    patches={
        "summer_mode_disable_temp": number("__test_replacement_1"),
    },
    service_parameters={
        0: number("__test_service_1"),
    },
)


def _dummy_module(
    attrs: dict[str, object], *, file_path: str | None = None
) -> ModuleType:
    """Create an in-memory module for custom parameter extraction tests."""
    module = ModuleType("pyplumio.parameters.custom.dummy")
    if file_path is not None:
        module.__file__ = file_path

    module.__dict__.update(attrs)
    return module


def test_dsl_factories() -> None:
    """Test custom_parameters, number, and switch factory functions."""
    num_default = number("boiler_temp")
    assert num_default == EcomaxNumberDescription(name="boiler_temp")

    num_string_unit = number(
        "heating_curve",
        step=0.1,
        offset=20,
        precision=2,
        optimistic=True,
        unit="°C",
    )
    assert num_string_unit == EcomaxNumberDescription(
        name="heating_curve",
        step=0.1,
        offset=20,
        precision=2,
        optimistic=True,
        unit_of_measurement=UnitOfMeasurement.CELSIUS,
    )

    num_percent = number("fan_power", unit="%")
    assert num_percent.unit_of_measurement == PERCENTAGE

    num_enum = number("draft", unit=UnitOfMeasurement.PASCAL)
    assert num_enum.unit_of_measurement == UnitOfMeasurement.PASCAL

    with pytest.raises(ValueError):
        number("invalid", unit="invalid")  # type: ignore[arg-type]

    sw = switch("thermostat", optimistic=True)
    assert sw == EcomaxSwitchDescription(name="thermostat", optimistic=True)

    empty_params = custom_parameters(model=DUMMY_MODEL, id=1)
    assert empty_params.service_parameters == {}
    assert empty_params.patches == {}
    assert empty_params.source is None
    assert empty_params.validate(
        ProductInfo(
            type=ProductType.ECOMAX_P,
            id=1,
            uid="*TEST*",
            logo=1,
            image=1,
            model=DUMMY_MODEL,
        )
    )
    assert not empty_params.validate(
        ProductInfo(
            type=ProductType.ECOMAX_P,
            id=2,
            uid="*TEST*",
            logo=1,
            image=1,
            model=DUMMY_MODEL,
        )
    )


def test_extract_custom_parameters(tmp_path: Path) -> None:
    """Test extract_custom_parameters fast path, fallback, and source handling."""
    fast_path = tmp_path / "ecomax_999_test.py"
    fast_module = _dummy_module(
        {"PARAMETERS": DUMMY_PARAMETERS},
        file_path=str(fast_path),
    )
    extracted = extract_custom_parameters(fast_module)
    assert extracted is not None
    assert extracted.model == DUMMY_MODEL
    assert extracted.source == fast_path

    fallback_module = _dummy_module({"CUSTOM_PARAMS": DUMMY_PARAMETERS})
    override_path = tmp_path / "custom" / "path.py"
    extracted_fallback = extract_custom_parameters(fallback_module, path=override_path)
    assert extracted_fallback is not None
    assert extracted_fallback.source == override_path

    no_file_module = _dummy_module({"PARAMETERS": DUMMY_PARAMETERS})
    extracted_no_file = extract_custom_parameters(no_file_module)
    assert extracted_no_file is not None
    assert extracted_no_file.source is None

    empty_module = _dummy_module({"PARAMETERS": "not_custom_params", "OTHER": 123})
    assert extract_custom_parameters(empty_module) is None


@pytest.mark.parametrize(
    ("product_info", "module_name", "attrs", "expected_result"),
    [
        (
            ProductInfo(
                type=ProductType.ECOMAX_P,
                id=1,
                uid="*TEST*",
                logo=1,
                image=1,
                model=DUMMY_MODEL,
            ),
            "ecomax_999_test",
            {"PARAMETERS": DUMMY_PARAMETERS},
            True,
        ),
        (
            ProductInfo(
                type=ProductType.ECOMAX_P,
                id=2,
                uid="*TEST*",
                logo=2,
                image=1,
                model=DUMMY_MODEL,
            ),
            "ecomax_999_test",
            {"PARAMETERS": DUMMY_PARAMETERS},
            False,
        ),
        (
            ProductInfo(
                type=ProductType.ECOMAX_P,
                id=1,
                uid="*TEST*",
                logo=1,
                image=1,
                model=f"{DUMMY_MODEL}2",
            ),
            "ecomax_999_test2",
            {"PARAMETERS": DUMMY_PARAMETERS},
            False,
        ),
        (
            ProductInfo(
                type=ProductType.ECOMAX_P,
                id=1,
                uid="*TEST*",
                logo=3,
                image=1,
                model=f"{DUMMY_MODEL}3",
            ),
            "ecomax_999_test3",
            {"OTHER": 123},
            False,
        ),
    ],
)
async def test_custom_parameters(
    product_info: ProductInfo,
    module_name: str,
    attrs: dict[str, object],
    expected_result: bool,
) -> None:
    """Test custom parameter patches and service parameter types."""
    dummy_module = _dummy_module(attrs)
    with patch(
        "pyplumio.parameters.custom.import_module", return_value=dummy_module
    ) as mock_import:
        parameters = await apply_custom_parameter_patches(
            product_info, parameter_types=ECOMAX_PARAMETER_TYPES[ProductType.ECOMAX_P]
        )
        replacement_found = any(
            parameter
            for parameter in parameters
            if parameter.name == "__test_replacement_1"
        )
        assert replacement_found is expected_result, (
            f"Replacements {'not' if expected_result else ''} found: {parameters}"
        )

        service_parameters = await get_custom_service_parameter_types(product_info)
        assert bool(service_parameters) is expected_result
        mock_import.assert_called_once_with(f"parameters.custom.{module_name}")


async def test_apply_custom_parameter_patches_empty_patches() -> None:
    """Test apply_custom_parameter_patches returns original list when no patches."""
    product_info = ProductInfo(
        type=ProductType.ECOMAX_P,
        id=99,
        uid="*TEST*",
        logo=0,
        image=0,
        model=f"{DUMMY_MODEL}4",
    )
    no_patch_module = _dummy_module(
        {
            "PARAMETERS": custom_parameters(
                model=f"{DUMMY_MODEL}4",
                id=99,
                service_parameters={0: number("test_param")},
            )
        }
    )
    original_types = ECOMAX_PARAMETER_TYPES[ProductType.ECOMAX_P]
    with patch(
        "pyplumio.parameters.custom.import_module", return_value=no_patch_module
    ):
        assert (
            await apply_custom_parameter_patches(product_info, original_types)
            is original_types
        )


async def test_load_custom_parameters_import_error() -> None:
    """Test load_custom_parameters returns None when module does not exist."""
    product_info = ProductInfo(
        type=ProductType.ECOMAX_P,
        id=999,
        uid="*MISSING*",
        logo=0,
        image=0,
        model="ecoMAX NONEXISTENT-MODEL",
    )
    assert await load_custom_parameters(product_info) is None


def test_model_slug() -> None:
    """Test model slug helper."""
    assert model_slug("ecoMAX 350P2-ZF") == "ecomax_350p2_zf"
    assert model_slug("ecoMAX 860P4-NM TOUCH") == "ecomax_860p4_nm_touch"


@pytest.mark.parametrize("module_name", CUSTOM_MODULE_NAMES)
async def test_custom_parameter_modules_consistency(module_name: str) -> None:
    """Verify every shipped custom parameter module follows project conventions."""
    module = await import_module(f"parameters.custom.{module_name}")
    params = getattr(module, "PARAMETERS", None)
    assert isinstance(params, CustomParameters)
    assert model_slug(params.model) == module_name
    assert isinstance(params.id, int) and not isinstance(params.id, bool)
    assert bool(params.service_parameters or params.patches)
    assert (TESTS_ROOT / "parameters" / "custom" / f"test_{module_name}.py").is_file()
    assert (TESTS_ROOT / "testdata" / "parameters" / f"{module_name}.json").is_file()
