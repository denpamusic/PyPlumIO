"""Contains a factory helper."""
from __future__ import annotations

import asyncio
from importlib import import_module
import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)


async def create_instance(class_path: str, **kwargs: Any) -> Any:
    """Return a class instance from the class path."""
    loop = asyncio.get_running_loop()
    module_name, class_name = class_path.rsplit(".", 1)
    try:
        module = await loop.run_in_executor(
            None, import_module, "." + module_name, "pyplumio"
        )
        return getattr(module, class_name)(**kwargs)
    except Exception:
        _LOGGER.error("Failed to load module (%s)", class_path)
        raise
