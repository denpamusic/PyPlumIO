"""Contains PyPlumIO command line interface."""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Sequence
from contextlib import suppress
import ctypes
import os
from pathlib import Path
import sys
import traceback
from typing import Final

from pyplumio.cli.session import DEFAULT_INTERVAL_SECONDS
from pyplumio.connection import DEFAULT_BAUDRATE

MAX_CONSOLE_PROCESSES: Final = 4
SIGINT_EXIT_CODE: Final = 130


def _is_standalone_windows_console() -> bool:
    """Return True if running in a dedicated Windows console window."""
    if (
        (windll := getattr(ctypes, "windll", None)) is None
        or not sys.stdin
        or not sys.stdin.isatty()
    ):
        return False

    try:
        process_ids = (ctypes.c_uint32 * MAX_CONSOLE_PROCESSES)()
        count = int(
            windll.kernel32.GetConsoleProcessList(process_ids, MAX_CONSOLE_PROCESSES)
        )
    except (AttributeError, OSError):
        return False

    own_pids = (
        {os.getpid(), os.getppid()} if getattr(sys, "frozen", False) else {os.getpid()}
    )
    return 0 < count <= len(own_pids) and set(process_ids[:count]) <= own_pids


def _pause_before_exit() -> None:
    """Pause before exiting so users can read error messages."""
    if _is_standalone_windows_console():
        sys.stderr.flush()
        with suppress(EOFError, KeyboardInterrupt):
            input("\nPress Enter to exit...")


def _parse_system_exit(err: SystemExit) -> int:
    """Convert SystemExit code to an integer exit status."""
    if isinstance(err.code, int):
        return err.code

    return 0 if err.code is None else 1


def _run_cli(argv: Sequence[str] | None) -> int:
    """Parse arguments and execute the CLI application."""
    try:
        from pyplumio.cli.app import run_app  # noqa: PLC0415
    except ImportError:
        sys.stderr.write(
            'PyPlumIO CLI requires extra dependencies: pip install "pyplumio[cli]"\n'
        )
        return 1

    parser = argparse.ArgumentParser(description="PyPlumIO parameter mapper.")
    parser.add_argument("--url", default=None, help="connection URL")
    parser.add_argument("--output", type=Path, default=Path.cwd(), help="output root")
    parser.add_argument(
        "--interval",
        type=float,
        default=DEFAULT_INTERVAL_SECONDS,
        help="poll interval",
    )
    parser.add_argument(
        "--baudrate", type=int, default=DEFAULT_BAUDRATE, help="baudrate"
    )
    parser.add_argument(
        "-z", "--zip", action="store_true", help="save output as a ZIP archive"
    )
    try:
        return asyncio.run(run_app(parser.parse_args(argv)))
    except KeyboardInterrupt:
        return SIGINT_EXIT_CODE
    except EOFError:
        return 1
    except SystemExit as err:
        return _parse_system_exit(err)
    except Exception:
        traceback.print_exc()
        return 1


def main(argv: Sequence[str] | None = None) -> int:
    """Run PyPlumIO command line interface."""
    exit_code = _run_cli(argv)
    if exit_code not in (0, SIGINT_EXIT_CODE):
        _pause_before_exit()

    return exit_code


__all__ = ("main",)
