"""Contains tests for the CLI initialization module."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from pyplumio.cli import main


def test_main_missing_dependencies(capsys: pytest.CaptureFixture[str]) -> None:
    """Test main when prompt_toolkit is missing."""
    with patch.dict("sys.modules", {"pyplumio.cli.app": None}):
        result = main([])
        assert result == 1
        captured = capsys.readouterr()
        assert (
            'PyPlumIO CLI requires extra dependencies: pip install "pyplumio[cli]"'
            in captured.err
        )


def test_main_with_arguments() -> None:
    """Test main with command-line arguments."""

    def fake_run(coro: Any) -> int:
        coro.close()
        return 0

    with (
        patch("asyncio.run", side_effect=fake_run) as mock_asyncio_run,
        patch("pyplumio.cli.app.run_app", new_callable=MagicMock) as mock_run_app,
    ):
        result = main(
            [
                "--url",
                "socket://localhost:8899",
                "--output",
                "test_output",
                "--interval",
                "1.5",
                "--baudrate",
                "9600",
            ]
        )
        assert result == 0
        mock_asyncio_run.assert_called_once()
        mock_run_app.assert_called_once()
        args = mock_run_app.call_args[0][0]
        assert args.url == "socket://localhost:8899"
        assert args.output == Path("test_output")
        assert args.interval == 1.5
        assert args.baudrate == 9600


def test_main_keyboard_interrupt() -> None:
    """Test main catches KeyboardInterrupt and returns 130."""

    def fake_run(coro: Any) -> int:
        coro.close()
        raise KeyboardInterrupt

    with patch("asyncio.run", side_effect=fake_run):
        result = main([])
        assert result == 130


def test_main_eof_error() -> None:
    """Test main catches EOFError and returns 1."""

    def fake_run(coro: Any) -> int:
        coro.close()
        raise EOFError

    with patch("asyncio.run", side_effect=fake_run):
        result = main([])
        assert result == 1
