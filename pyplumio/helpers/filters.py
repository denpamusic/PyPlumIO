"""Contains callback filters."""

from warnings import warn

from pyplumio.filters import Filter, aggregate, debounce, delta, on_change, throttle

warn(
    "pyplumio.helpers.filters module is deprecated and will be removed in v0.4.1. "
    + "Please use pyplumio.filters module.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["Filter", "aggregate", "debounce", "delta", "on_change", "throttle"]
