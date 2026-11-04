"""Contains PyPlumIO command line interface."""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Sequence
from pathlib import Path
import sys


def main(argv: Sequence[str] | None = None) -> int:
    """Run PyPlumIO command line interface."""
    try:
        from pyplumio.cli.app import run_app  # noqa: PLC0415
    except ImportError:
        print(  # noqa: T201
            'PyPlumIO CLI requires extra dependencies: pip install "pyplumio[cli]"',
            file=sys.stderr,
        )
        return 1

    parser = argparse.ArgumentParser(description="PyPlumIO parameter mapper.")
    parser.add_argument("--url", default=None, help="connection URL")
    parser.add_argument("--output", type=Path, default=Path.cwd(), help="output root")
    parser.add_argument("--interval", type=float, default=2.0, help="poll interval")
    parser.add_argument("--baudrate", type=int, default=115200, help="baudrate")
    return asyncio.run(run_app(parser.parse_args(argv)))


__all__ = ("main",)
