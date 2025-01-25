"""Contains a factory helper."""

from __future__ import annotations

import asyncio
import importlib
import logging
from types import ModuleType
from typing import Any, TypeVar

_LOGGER = logging.getLogger(__name__)

T = TypeVar("T")


async def _import_module(name: str) -> ModuleType:
    """Import module by name."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, importlib.import_module, f"pyplumio.{name}")


async def create_instance(class_path: str, cls: type[T], **kwargs: Any) -> T:
    """Return a class instance from the class path."""
    module_name, class_name = class_path.rsplit(".", 1)
    try:
        module = await _import_module(module_name)
        instance = getattr(module, class_name)(**kwargs)
        if not isinstance(instance, cls):
            raise TypeError(
                f"Expected instance of '{cls.__name__}', but got "
                f"'{type(instance).__name__}' from '{class_name}'"
            )

        return instance
    except Exception:
        _LOGGER.exception("Failed to create instance for class path '%s'", class_path)
        raise
