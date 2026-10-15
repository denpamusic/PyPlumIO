"""Contains tests for the program version structure decoder."""

from importlib.metadata import PackageNotFoundError
import re
from unittest.mock import patch

from pyplumio.structures.program_version import SOFTWARE_VERSION, _get_software_version


def test_software_version_format() -> None:
    """Test that SOFTWARE_VERSION is exactly 3 dot-separated integers."""
    assert SOFTWARE_VERSION == "0.7.0"
    assert re.fullmatch(r"^\d+\.\d+\.\d+$", SOFTWARE_VERSION) is not None


def test_get_software_version_edge_cases() -> None:
    """Test version extraction with different version formats."""
    cases = [
        ("0.7.0", "0.7.0"),
        ("0.7.0.post1", "0.7.0"),
        ("0.7.0rc1", "0.7.0"),
        ("0.7.0.dev11+g9ba8202f7", "0.7.0"),
        ("1.2", "1.2.0"),
        ("3", "3.0.0"),
        ("2.1.4.5", "2.1.4"),
    ]
    for input_version, expected in cases:
        with patch(
            "pyplumio.structures.program_version._pkg_version",
            return_value=input_version,
        ):
            result = _get_software_version()
            assert result == expected
            assert re.fullmatch(r"^\d+\.\d+\.\d+$", result) is not None


def test_get_software_version_not_found() -> None:
    """Test fallback when package is not found."""
    with patch(
        "pyplumio.structures.program_version._pkg_version",
        side_effect=PackageNotFoundError,
    ):
        result = _get_software_version()
        assert result == "0.0.0"
        assert re.fullmatch(r"^\d+\.\d+\.\d+$", result) is not None
