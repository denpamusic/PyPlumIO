"""Custom parameters for products."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import logging
from typing import ClassVar, NamedTuple, TypeVar, cast

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


class ParameterOverride(NamedTuple):
    """Represents a parameter override."""

    original: str
    replacement: ParameterDescription


@dataclass(frozen=True, slots=True)
class ParameterOverload:
    """Represents a parameter overload."""

    name: str


def overload(name: str) -> ParameterOverload:
    """Mark that parameter overloads the standard one with same name."""
    return ParameterOverload(name)


class CustomParameters:
    """Represents a custom parameters."""

    __slots__ = ()

    # Device signature.
    signature: ClassVar[Signature]

    # Overrides descriptions in standard parameter table.
    overrides: ClassVar[Sequence[ParameterOverride]] = []

    # Service parameters descriptions.
    descriptions: ClassVar[dict[int, ParameterDescription | ParameterOverload]] = {}

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


async def get_custom_service_parameter_types(
    product_info: ProductInfo,
) -> dict[int, ParameterDescription | ParameterOverload]:
    """Get custom service parameter types."""
    if custom_parameters := await _load_custom_parameters(product_info):
        return custom_parameters.descriptions

    return {}


async def inject_custom_parameter_overrides(
    product_info: ProductInfo, parameter_types: list[_DescriptionT]
) -> list[_DescriptionT]:
    """Patch the parameter types based on the provided overrides."""
    if custom_parameters := await _load_custom_parameters(product_info):
        if overrides := dict(custom_parameters.overrides):
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


__all__ = (
    "CustomParameters",
    "ParameterOverride",
    "ParameterOverload",
    "Signature",
    "overload",
    "get_custom_service_parameter_types",
    "inject_custom_parameter_overrides",
)
