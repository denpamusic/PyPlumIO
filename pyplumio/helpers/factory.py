"""Contains a factory helper."""

from __future__ import annotations

import asyncio
import importlib
import logging
from types import ModuleType
from typing import Any, TypeVar

_LOGGER = logging.getLogger(__name__)

T = TypeVar("T")


async def _load_module(module_name: str) -> ModuleType:
    """Load a module by name."""
    return await asyncio.get_running_loop().run_in_executor(
        None, importlib.import_module, f".{module_name}", "pyplumio"
    )


async def create_instance(class_path: str, cls: type[T], **kwargs: Any) -> T:
    """Return a class instance from the class path."""
    module_name, class_name = class_path.rsplit(".", 1)
    try:
        module = await _load_module(module_name)
        instance = getattr(module, class_name)(**kwargs)
        if not isinstance(instance, cls):
            raise TypeError(f"class '{class_name}' should be derived from {cls}")

        return instance
    except Exception:
        _LOGGER.error("Failed to load module (%s)", class_path)
        raise
