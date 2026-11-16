"""Custom parameters for products."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
import logging
from pathlib import Path
from types import MappingProxyType, ModuleType
from typing import TYPE_CHECKING, Literal, TypeVar, cast

from pyplumio.const import PERCENTAGE, UnitOfMeasurement, UnitValue
from pyplumio.helpers.async_cache import acache
from pyplumio.structures.product_info import ProductInfo
from pyplumio.utils import import_module

if TYPE_CHECKING:
    from pyplumio.parameters.ecomax import (
        EcomaxNumberDescription,
        EcomaxParameterDescription,
        EcomaxSwitchDescription,
    )

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True, kw_only=True)
class CustomParameters:
    """Represents custom parameters for a product."""

    model: str
    id: int
    service_parameters: Mapping[int, EcomaxParameterDescription] = field(
        default_factory=lambda: MappingProxyType({})
    )
    patches: Mapping[str, EcomaxParameterDescription] = field(
        default_factory=lambda: MappingProxyType({})
    )
    source: Path | None = None

    def validate(self, product_info: ProductInfo) -> bool:
        """Validate the product info."""
        return self.id == product_info.id and self.model == product_info.model


def _resolve_unit(
    unit: UnitOfMeasurement | UnitValue | None,
) -> UnitOfMeasurement | Literal["%"] | None:
    """Resolve unit literal or enum to UnitOfMeasurement or PERCENTAGE."""
    if unit is None:
        return None

    if unit == PERCENTAGE:
        return PERCENTAGE

    return unit if isinstance(unit, UnitOfMeasurement) else UnitOfMeasurement(unit)


def number(
    name: str,
    *,
    step: float = 1.0,
    offset: int = 0,
    precision: int = 6,
    optimistic: bool = False,
    unit: UnitOfMeasurement | UnitValue | None = None,
) -> EcomaxNumberDescription:
    """Return an ecoMAX number parameter description."""
    from pyplumio.parameters.ecomax import EcomaxNumberDescription  # noqa: PLC0415

    return EcomaxNumberDescription(
        name=name,
        step=step,
        offset=offset,
        precision=precision,
        optimistic=optimistic,
        unit_of_measurement=_resolve_unit(unit),
    )


def switch(name: str, *, optimistic: bool = False) -> EcomaxSwitchDescription:
    """Return an ecoMAX switch parameter description."""
    from pyplumio.parameters.ecomax import EcomaxSwitchDescription  # noqa: PLC0415

    return EcomaxSwitchDescription(name=name, optimistic=optimistic)


def custom_parameters(
    *,
    model: str,
    id: int,
    service_parameters: Mapping[int, EcomaxParameterDescription] | None = None,
    patches: Mapping[str, EcomaxParameterDescription] | None = None,
) -> CustomParameters:
    """Return custom parameters for a device model."""
    return CustomParameters(
        model=model,
        id=id,
        service_parameters=MappingProxyType(dict(service_parameters or {})),
        patches=MappingProxyType(dict(patches or {})),
    )


def model_slug(model: str) -> str:
    """Return model slug from model name."""
    return model.replace("-", "_").replace(" ", "_").lower()


def extract_custom_parameters(
    module: ModuleType, *, path: Path | None = None
) -> CustomParameters | None:
    """Extract custom parameters instance from a loaded module."""
    params = getattr(module, "PARAMETERS", None)
    if not isinstance(params, CustomParameters):
        params = next(
            (
                value
                for value in vars(module).values()
                if isinstance(value, CustomParameters)
            ),
            None,
        )

    if params is None:
        return None

    if path is not None:
        return replace(params, source=path)

    if module_file := getattr(module, "__file__", None):
        return replace(params, source=Path(module_file))

    return params


@acache
async def load_custom_parameters(product_info: ProductInfo) -> CustomParameters | None:
    """Load custom parameters."""
    module_name = model_slug(product_info.model)
    module_path = f"parameters.custom.{module_name}"
    try:
        _LOGGER.debug(
            "Trying to load custom parameters for %s from %s",
            product_info.model,
            module_path,
        )
        module = await import_module(module_path)
        loaded_parameters = extract_custom_parameters(module)
        if loaded_parameters is None or not loaded_parameters.validate(product_info):
            raise ValueError
    except (ImportError, TypeError, ValueError):
        _LOGGER.debug("No custom parameters found for %s", product_info.model)
        return None

    _LOGGER.debug("Custom parameters loaded for %s", product_info.model)
    return loaded_parameters


_DescriptionT = TypeVar("_DescriptionT", bound="EcomaxParameterDescription")


async def get_custom_service_parameter_types(
    product_info: ProductInfo,
) -> dict[int, EcomaxParameterDescription]:
    """Get custom service parameter types."""
    if loaded_parameters := await load_custom_parameters(product_info):
        return dict(loaded_parameters.service_parameters)

    return {}


async def apply_custom_parameter_patches(
    product_info: ProductInfo, parameter_types: list[_DescriptionT]
) -> list[_DescriptionT]:
    """Patch the parameter types based on the provided patches."""
    if loaded_parameters := await load_custom_parameters(product_info):
        if patches := loaded_parameters.patches:
            return cast(
                list[_DescriptionT],
                [
                    replacement
                    if original.name in patches
                    and (replacement := patches[original.name])
                    and (base_class := original.__class__.__bases__[0])
                    and isinstance(replacement, base_class)
                    else original
                    for original in parameter_types
                ],
            )

    return parameter_types


__all__ = (
    "CustomParameters",
    "UnitValue",
    "apply_custom_parameter_patches",
    "custom_parameters",
    "extract_custom_parameters",
    "get_custom_service_parameter_types",
    "load_custom_parameters",
    "model_slug",
    "number",
    "switch",
)
