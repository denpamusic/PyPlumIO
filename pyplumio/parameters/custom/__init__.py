"""Custom parameters for products."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import logging
from typing import ClassVar, TypeVar, cast

from pyplumio.helpers.factory import create_instance
from pyplumio.parameters import ParameterDescription
from pyplumio.structures.product_info import ProductInfo
from pyplumio.utils import to_camelcase

_LOGGER = logging.getLogger(__name__)


@dataclass
class Signature:
    """Represents a product signature."""

    __slots__ = ("id", "model")

    id: int
    model: str


@dataclass
class CustomParameter:
    """Represents a custom parameter."""

    __slots__ = ("original", "replacement")

    original: str
    replacement: ParameterDescription


class CustomParameters:
    """Represents a custom parameters."""

    signature: ClassVar[Signature]
    replacements: ClassVar[Sequence[CustomParameter]]

    def validate(self, product_info: ProductInfo) -> bool:
        """Validate the product info."""
        return (
            self.signature.id == product_info.id
            and self.signature.model == product_info.model
        )


async def _load_custom_parameters(
    product_info: ProductInfo,
) -> dict[str, ParameterDescription] | None:
    """Load custom parameters."""
    module_name = product_info.model.replace("-", "_").replace(" ", "_").lower()
    module_path = f"parameters.custom.{module_name}"
    class_name = to_camelcase(module_name).upper().replace("ECOMAX", "EcoMAX")
    class_path = f"{module_path}.{class_name}"
    try:
        _LOGGER.debug(
            "Trying to load custom parameters for %s from %s",
            product_info.model,
            class_path,
        )
        custom_parameters = await create_instance(class_path, cls=CustomParameters)
        if not custom_parameters.validate(product_info):
            raise ValueError
    except (ImportError, TypeError, ValueError):
        _LOGGER.debug("No custom parameters found for %s", product_info.model)
        return None

    return {
        custom_parameter.original: custom_parameter.replacement
        for custom_parameter in custom_parameters.replacements
    }


_DescriptionT = TypeVar("_DescriptionT", bound=ParameterDescription)


async def inject_custom_parameters(
    product_info: ProductInfo, parameter_types: list[_DescriptionT]
) -> list[_DescriptionT]:
    """Patch the parameter types based on the provided overrides."""
    if custom_parameters := await _load_custom_parameters(product_info):
        _LOGGER.debug("Custom parameters found for %s", product_info.model)
        return cast(
            list[_DescriptionT],
            [
                replacement
                if original.name in custom_parameters
                and (replacement := custom_parameters[original.name])
                and (base_class := original.__class__.__bases__[0])
                and isinstance(replacement, base_class)
                else original
                for original in parameter_types
            ],
        )

    return parameter_types


__all__ = (
    "inject_custom_parameters",
    "CustomParameters",
    "CustomParameter",
    "Signature",
)
