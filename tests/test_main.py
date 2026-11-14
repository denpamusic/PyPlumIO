"""Contains tests for the main module."""

from __future__ import annotations

import runpy
from unittest.mock import patch

import pytest


def test_main() -> None:
    """Test entry point execution."""
    with (
        patch("pyplumio.cli.main", return_value=0) as mock_cli_main,
        pytest.raises(SystemExit) as exc_info,
    ):
        runpy.run_module("pyplumio.__main__", run_name="__main__")

    assert exc_info.value.code == 0
    mock_cli_main.assert_called_once()
