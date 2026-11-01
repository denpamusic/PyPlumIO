"""Custom parameters for products."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import logging
from typing import ClassVar, TypeVar, cast

from pyplumio.helpers.async_cache import acache
from pyplumio.parameters import ParameterDescription
from pyplumio.structures.product_info import ProductInfo
from pyplumio.utils import create_instance, to_camelcase

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True, kw_only=True)
class Signature:
    """Represents a product signature."""

    id: int
    model: str


@dataclass(slots=True, kw_only=True)
class ParameterOverride:
    """Represents a parameter override."""

    original: str
    replacement: ParameterDescription


class CustomParameters:
    """Represents a custom parameters."""

    __slots__ = ()

    signature: ClassVar[Signature]
    replacements: ClassVar[Sequence[ParameterOverride]] = ()
    extended: ClassVar[dict[int, ParameterDescription]] = {}

    def validate(self, product_info: ProductInfo) -> bool:
        """Validate the product info."""
        return (
            self.signature.id == product_info.id
            and self.signature.model == product_info.model
        )


@acache
async def _load_custom_parameters(
    product_info: ProductInfo,
) -> CustomParameters | None:
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

    _LOGGER.debug("Custom parameters loaded for %s", product_info.model)
    return custom_parameters


_DescriptionT = TypeVar("_DescriptionT", bound=ParameterDescription)


async def inject_custom_parameter_overrides(
    product_info: ProductInfo, parameter_types: list[_DescriptionT]
) -> list[_DescriptionT]:
    """Patch the parameter types based on the provided overrides."""
    if custom_parameters := await _load_custom_parameters(product_info):
        if overrides := {
            override.original: override.replacement
            for override in custom_parameters.replacements
        }:
            return cast(
                list[_DescriptionT],
                [
                    replacement
                    if original.name in overrides
                    and (replacement := overrides[original.name])
                    and (base_class := original.__class__.__bases__[0])
                    and isinstance(replacement, base_class)
                    else original
                    for original in parameter_types
                ],
            )

    return parameter_types


async def get_custom_extended_parameter_types(
    product_info: ProductInfo,
) -> dict[int, ParameterDescription]:
    """Get custom extended parameter types."""
    if custom_parameters := await _load_custom_parameters(product_info):
        return custom_parameters.extended

    return {}


__all__ = (
    "CustomParameters",
    "ParameterOverride",
    "Signature",
    "get_custom_extended_parameter_types",
    "inject_custom_parameter_overrides",
)
