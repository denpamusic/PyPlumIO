"""Contains tests for the main module."""

from __future__ import annotations

import runpy
from unittest.mock import patch


def test_main() -> None:
    """Test entry point execution."""
    with patch("pyplumio.cli.main") as mock_cli_main:
        runpy.run_module("pyplumio.__main__", run_name="__main__")
        mock_cli_main.assert_called_once()
