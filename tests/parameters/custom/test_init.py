"""Contains tests for the custom parameter descriptors."""

from unittest.mock import patch

import pytest

from pyplumio.const import ProductType
from pyplumio.parameters.custom import (
    CustomParameter,
    CustomParameters,
    Signature,
    inject_custom_parameters,
)
from pyplumio.parameters.ecomax import (
    PARAMETER_TYPES as ECOMAX_PARAMETER_TYPES,
    EcomaxNumberDescription,
)
from pyplumio.structures.product_info import ProductInfo


class DummyEcoMAX(CustomParameters):
    """Replacements for ecoMAX 860D3-HB."""

    __slots__ = ()

    signature = Signature(model="ecoMAX Dummy", id=1)

    replacements = (
        CustomParameter(
            original="summer_mode_disable_temp",
            replacement=EcomaxNumberDescription(name="__test_replacement_1"),
        ),
    )


@pytest.mark.parametrize(
    ("product_info", "module_name", "expected_result"),
    [
        (
            ProductInfo(
                type=ProductType.ECOMAX_P,
                id=1,
                uid="*TEST*",
                logo=1,
                image=1,
                model="ecoMAX Dummy",
            ),
            "ecomax_dummy.EcoMAXDUMMY",
            True,
        ),
        (
            ProductInfo(
                type=ProductType.ECOMAX_P,
                id=2,
                uid="*TEST*",
                logo=2,
                image=1,
                model="ecoMAX Dummy",
            ),
            "ecomax_dummy.EcoMAXDUMMY",
            False,
        ),
        (
            ProductInfo(
                type=ProductType.ECOMAX_P,
                id=1,
                uid="*TEST*",
                logo=1,
                image=1,
                model="ecoMAX Dummy2",
            ),
            "ecomax_dummy2.EcoMAXDUMMY2",
            False,
        ),
    ],
)
@patch("pyplumio.parameters.custom.create_instance", return_value=DummyEcoMAX())
async def test_inject_custom_parameters(
    moke_create_instance,
    product_info: ProductInfo,
    expected_result: bool,
    module_name: str,
) -> None:
    """Test custom parameters injection."""
    parameters = await inject_custom_parameters(
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
    moke_create_instance.assert_called_once_with(
        f"parameters.custom.{module_name}", cls=CustomParameters
    )
