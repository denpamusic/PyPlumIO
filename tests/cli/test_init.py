"""Contains tests for the CLI initialization module."""

from __future__ import annotations

import ctypes
import os
from pathlib import Path
import sys
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from pyplumio.cli import _is_standalone_windows_console, _pause_before_exit, main


def test_main_missing_dependencies(capsys: pytest.CaptureFixture[str]) -> None:
    """Test main when prompt_toolkit is missing."""
    with (
        patch.dict("sys.modules", {"pyplumio.cli.app": None}),
        patch("pyplumio.cli._pause_before_exit") as mock_pause,
    ):
        result = main([])
        assert result == 1
        captured = capsys.readouterr()
        assert (
            'PyPlumIO CLI requires extra dependencies: pip install "pyplumio[cli]"'
            in captured.err
        )
        mock_pause.assert_called_once()


def test_main_with_arguments() -> None:
    """Test main with command-line arguments."""

    def fake_run(coro: Any) -> int:
        coro.close()
        return 0

    with (
        patch("asyncio.run", side_effect=fake_run) as mock_asyncio_run,
        patch("pyplumio.cli.app.run_app", new_callable=MagicMock) as mock_run_app,
        patch("pyplumio.cli._pause_before_exit") as mock_pause,
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
        mock_pause.assert_not_called()
        args = mock_run_app.call_args[0][0]
        assert args.url == "socket://localhost:8899"
        assert args.output == Path("test_output")
        assert args.interval == 1.5
        assert args.baudrate == 9600
        assert args.zip is False


@pytest.mark.parametrize("flag", ["-z", "--zip"])
def test_main_zip_flag(flag: str) -> None:
    """Test main with -z and --zip flags."""

    def fake_run(coro: Any) -> int:
        coro.close()
        return 0

    with (
        patch("asyncio.run", side_effect=fake_run),
        patch("pyplumio.cli.app.run_app", new_callable=MagicMock) as mock_run_app,
    ):
        result = main([flag])
        assert result == 0
        args = mock_run_app.call_args[0][0]
        assert args.zip is True


def test_main_keyboard_interrupt() -> None:
    """Test main catches KeyboardInterrupt and returns 130 without pausing."""

    def fake_run(coro: Any) -> int:
        coro.close()
        raise KeyboardInterrupt

    with (
        patch("asyncio.run", side_effect=fake_run),
        patch("pyplumio.cli._pause_before_exit") as mock_pause,
    ):
        result = main([])
        assert result == 130
        mock_pause.assert_not_called()


def test_main_eof_error() -> None:
    """Test main catches EOFError and returns 1."""

    def fake_run(coro: Any) -> int:
        coro.close()
        raise EOFError

    with (
        patch("asyncio.run", side_effect=fake_run),
        patch("pyplumio.cli._pause_before_exit") as mock_pause,
    ):
        result = main([])
        assert result == 1
        mock_pause.assert_called_once()


def test_main_help_and_invalid_argument() -> None:
    """Test main handles SystemExit for --help and invalid arguments."""
    with patch("pyplumio.cli._pause_before_exit") as mock_pause:
        assert main(["--help"]) == 0
        mock_pause.assert_not_called()

        assert main(["--unknown-flag"]) == 2
        mock_pause.assert_called_once()


def test_main_non_int_system_exit() -> None:
    """Test main handles SystemExit with non-integer code."""
    with (
        patch("argparse.ArgumentParser.parse_args", side_effect=SystemExit(None)),
        patch("pyplumio.cli._pause_before_exit") as mock_pause,
    ):
        assert main([]) == 0
        mock_pause.assert_not_called()

    with (
        patch("argparse.ArgumentParser.parse_args", side_effect=SystemExit("boom")),
        patch("pyplumio.cli._pause_before_exit") as mock_pause,
    ):
        assert main([]) == 1
        mock_pause.assert_called_once()


def test_main_unexpected_exception(capsys: pytest.CaptureFixture[str]) -> None:
    """Test main catches unexpected exceptions, prints traceback, and pauses."""

    def fake_run(coro: Any) -> int:
        coro.close()
        raise RuntimeError("unexpected failure")

    with (
        patch("asyncio.run", side_effect=fake_run),
        patch("pyplumio.cli._pause_before_exit") as mock_pause,
    ):
        result = main([])
        assert result == 1
        assert "RuntimeError: unexpected failure" in capsys.readouterr().err
        mock_pause.assert_called_once()


def test_is_standalone_windows_console_no_windll() -> None:
    """Test standalone console check returns False without windll."""
    with patch.object(ctypes, "windll", None, create=True):
        assert _is_standalone_windows_console() is False


def test_is_standalone_windows_console_non_tty() -> None:
    """Test standalone console check returns False when stdin is not a TTY."""
    mock_stdin = MagicMock()
    mock_stdin.isatty.return_value = False
    with (
        patch.object(ctypes, "windll", MagicMock(), create=True),
        patch.object(sys, "stdin", mock_stdin),
    ):
        assert _is_standalone_windows_console() is False


def test_is_standalone_windows_console_win32_error() -> None:
    """Test standalone console check handles Win32 API errors."""
    mock_stdin = MagicMock()
    mock_stdin.isatty.return_value = True
    mock_windll = MagicMock()
    mock_windll.kernel32.GetConsoleProcessList.side_effect = OSError("fail")
    with (
        patch.object(ctypes, "windll", mock_windll, create=True),
        patch.object(sys, "stdin", mock_stdin),
    ):
        assert _is_standalone_windows_console() is False


@pytest.mark.parametrize(
    ("pids", "frozen", "expected"),
    [
        ([], False, False),
        ([os.getpid()], False, True),
        ([os.getpid(), 999999], False, False),
        ([os.getpid(), os.getppid()], True, True),
        ([os.getpid(), os.getppid(), 999999], True, False),
    ],
)
def test_is_standalone_windows_console_process_counts(
    pids: list[int], frozen: bool, expected: bool
) -> None:
    """Test standalone console detection across frozen and terminal cases."""
    mock_stdin = MagicMock()
    mock_stdin.isatty.return_value = True

    def fake_get_console_process_list(buf: Any, _size: int) -> int:
        for idx, pid in enumerate(pids):
            buf[idx] = pid
        return len(pids)

    mock_windll = MagicMock()
    mock_windll.kernel32.GetConsoleProcessList.side_effect = (
        fake_get_console_process_list
    )
    with (
        patch.object(ctypes, "windll", mock_windll, create=True),
        patch.object(sys, "stdin", mock_stdin),
        patch.object(sys, "frozen", frozen, create=True),
    ):
        assert _is_standalone_windows_console() is expected


def test_pause_before_exit() -> None:
    """Test _pause_before_exit prompts when in standalone console and suppresses EOF."""
    with (
        patch("pyplumio.cli._is_standalone_windows_console", return_value=True),
        patch("builtins.input", side_effect=EOFError) as mock_input,
    ):
        _pause_before_exit()
        mock_input.assert_called_once_with("\nPress Enter to exit...")

    with (
        patch("pyplumio.cli._is_standalone_windows_console", return_value=False),
        patch("builtins.input") as mock_input,
    ):
        _pause_before_exit()
        mock_input.assert_not_called()
