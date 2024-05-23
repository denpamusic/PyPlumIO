"""Contains a factory helper."""

from __future__ import annotations

import asyncio
import importlib
import logging
from types import ModuleType
from typing import Any

_LOGGER = logging.getLogger(__name__)


async def _load_module(module_name: str) -> ModuleType:
    """Load a module by name."""
    return await asyncio.get_running_loop().run_in_executor(
        None, importlib.import_module, f".{module_name}", "pyplumio"
    )


async def create_instance(class_path: str, **kwargs: Any) -> Any:
    """Return a class instance from the class path."""
    module_name, class_name = class_path.rsplit(".", 1)
    try:
        module = await _load_module(module_name)
        return getattr(module, class_name)(**kwargs)
    except Exception:
        _LOGGER.error("Failed to load module (%s)", class_path)
        raise
