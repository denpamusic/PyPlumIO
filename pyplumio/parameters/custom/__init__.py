"""Custom parameters for products."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import logging
from typing import TYPE_CHECKING, ClassVar, NamedTuple, TypeVar, cast

from pyplumio.helpers.async_cache import acache
from pyplumio.structures.product_info import ProductInfo
from pyplumio.utils import create_instance, to_camelcase

if TYPE_CHECKING:
    from pyplumio.parameters.ecomax import EcomaxParameterDescription

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True, kw_only=True)
class Signature:
    """Represents a product signature."""

    id: int
    model: str


class ParameterOverride(NamedTuple):
    """Represents a parameter override."""

    original: str
    replacement: EcomaxParameterDescription


class CustomParameters:
    """Represents a custom parameters."""

    __slots__ = ()

    # Device signature.
    signature: ClassVar[Signature]

    # Overrides descriptions in standard parameter table.
    overrides: ClassVar[Sequence[ParameterOverride]] = []

    # Service parameters descriptions.
    descriptions: ClassVar[dict[int, EcomaxParameterDescription]] = {}

    def validate(self, product_info: ProductInfo) -> bool:
        """Validate the product info."""
        return (
            self.signature.id == product_info.id
            and self.signature.model == product_info.model
        )


def model_slug(model: str) -> str:
    """Return model slug from model name."""
    return model.replace("-", "_").replace(" ", "_").lower()


def custom_class_name(slug: str) -> str:
    """Return custom parameter class name from model slug."""
    return to_camelcase(slug).upper().replace("ECOMAX", "EcoMAX")


@acache
async def _load_custom_parameters(product_info: ProductInfo) -> CustomParameters | None:
    """Load custom parameters."""
    module_name = model_slug(product_info.model)
    module_path = f"parameters.custom.{module_name}"
    class_name = custom_class_name(module_name)
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


_DescriptionT = TypeVar("_DescriptionT", bound="EcomaxParameterDescription")


async def get_custom_service_parameter_types(
    product_info: ProductInfo,
) -> dict[int, EcomaxParameterDescription]:
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
    "Signature",
    "custom_class_name",
    "get_custom_service_parameter_types",
    "inject_custom_parameter_overrides",
    "model_slug",
)
