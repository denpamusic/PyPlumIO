"""Contains tests for callback filters."""

import warnings

from pyplumio import filters


# pylint: disable=import-outside-toplevel
def test_deprecated_message() -> None:
    """Test deprecated message."""
    with warnings.catch_warnings(record=True) as warn:
        warnings.simplefilter("always")
        from pyplumio.helpers import filters as deprecated

        assert len(warn) == 1
        assert issubclass(warn[-1].category, DeprecationWarning)
        assert "deprecated" in str(warn[-1].message)
        assert deprecated.aggregate == filters.aggregate
        assert deprecated.debounce == filters.debounce
        assert deprecated.delta == filters.delta
        assert deprecated.on_change == filters.on_change
        assert deprecated.throttle == filters.throttle
