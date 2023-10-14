"""Contains a factory helper."""
from __future__ import annotations

import importlib
import logging

_LOGGER = logging.getLogger(__name__)


def factory(class_path: str, **kwargs):
    """Return class instance from the class path."""
    try:
        module_name, class_name = class_path.rsplit(".", 1)
        return getattr(
            importlib.import_module("." + module_name, "pyplumio"), class_name
        )(**kwargs)
    except Exception:
        _LOGGER.error("Failed to load module (%s)", class_path)
        raise
