"""Contains PyPlumIO CLI application runner and connection prompts."""

from __future__ import annotations

import argparse
from collections.abc import Iterator, Sequence
from contextlib import contextmanager, suppress
from enum import StrEnum, unique
import inspect
import logging
from pathlib import Path
import sys
from typing import Final

from prompt_toolkit.application import Application
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.shortcuts import PromptSession
from prompt_toolkit.validation import Validator
from serialx import SerialException

from pyplumio.cli.codegen import custom_module_path, extract_comments
from pyplumio.cli.model import ParameterTable
from pyplumio.cli.session import Session
from pyplumio.cli.state import AppState
from pyplumio.cli.ui import create_app
from pyplumio.exceptions import PyPlumIOError
from pyplumio.parameters import ParameterValues
from pyplumio.parameters.custom import (
    CustomParameters,
    load_custom_parameters,
    model_slug,
)


@unique
class _ConnectionType(StrEnum):
    """Contains connection types."""

    TCP = "tcp"
    SERIAL = "serial"


DEFAULT_PORT: Final = 8899
MAX_PORT: Final = 65535
AVAILABLE_CONNECTION_TYPES: Final = ", ".join(_ConnectionType)
CONNECTION_TYPE_COMPLETER: Final = WordCompleter(list(_ConnectionType))
CONNECTION_TYPE_VALIDATOR: Final = Validator.from_callable(
    lambda text: text.strip().lower() in list(_ConnectionType),
    error_message=f"Must be one of the following: {AVAILABLE_CONNECTION_TYPES}",
)
HOST_VALIDATOR: Final = Validator.from_callable(
    lambda text: bool(text.strip()), error_message="Host cannot be empty"
)
PORT_VALIDATOR: Final = Validator.from_callable(
    lambda text: (
        not text.strip() or (text.strip().isdigit() and 1 <= int(text) <= MAX_PORT)
    ),
    error_message=f"Port must be 1-{MAX_PORT}",
)
URL_VALIDATOR: Final = Validator.from_callable(
    lambda text: bool(text.strip()), error_message="URL cannot be empty"
)


class _StatusLogHandler(logging.Handler):
    """Represents a log handler routing warnings to app status."""

    __slots__ = ("_state",)

    _state: AppState

    def __init__(self, state: AppState) -> None:
        """Initialize the status log handler."""
        super().__init__(level=logging.WARNING)
        self._state = state

    def emit(self, record: logging.LogRecord) -> None:
        """Emit log message to app status."""
        self._state.status = self.format(record)
        if self._state.application:
            self._state.application.invalidate()


@contextmanager
def _capture_logs(state: AppState) -> Iterator[None]:
    """Route pyplumio logger warnings to app status while active."""
    pyplumio_logger = logging.getLogger("pyplumio")
    original_handlers = pyplumio_logger.handlers[:]
    original_propagate = pyplumio_logger.propagate
    pyplumio_logger.handlers = [_StatusLogHandler(state)]
    pyplumio_logger.propagate = False
    try:
        yield
    finally:
        pyplumio_logger.handlers = original_handlers
        pyplumio_logger.propagate = original_propagate


def _format_error(err: BaseException) -> str:
    """Return formatted error message with cause fallback."""
    if message := str(err):
        return message

    if err.__cause__:
        return f"{type(err).__name__}: {err.__cause__}"

    return type(err).__name__


def _write_status(message: str) -> None:
    """Write status message to standard error."""
    sys.stderr.write(f"{message}\n")
    sys.stderr.flush()


def _load_comments(
    custom_parameters: CustomParameters, output_dir: Path, slug: str
) -> dict[int, str]:
    """Load parameter comments from output directory or module source."""
    path = custom_module_path(output_dir, slug)
    if not path.is_file() and (
        source_file := inspect.getsourcefile(type(custom_parameters))
    ):
        path = Path(source_file)

    if path.is_file():
        with suppress(OSError):
            return extract_comments(path.read_text(encoding="utf-8"))

    return {}


async def prompt_connection_url(
    session: PromptSession[str] | None = None,
) -> str:
    """Prompt user for connection details and return the connection URL."""
    if not session:
        session = PromptSession()

    connection_type = await session.prompt_async(
        f"Connection type ({AVAILABLE_CONNECTION_TYPES}): ",
        completer=CONNECTION_TYPE_COMPLETER,
        validator=CONNECTION_TYPE_VALIDATOR,
    )
    connection_type = connection_type.strip().lower()

    if connection_type == _ConnectionType.TCP:
        host = await session.prompt_async("Host: ", validator=HOST_VALIDATOR)
        host = host.strip()
        port = await session.prompt_async(
            f"Port [{DEFAULT_PORT}]: ", validator=PORT_VALIDATOR
        )
        if not (port := port.strip()):
            port = str(DEFAULT_PORT)

        return f"socket://{host}:{port}"

    url = await session.prompt_async(
        "Device URL (e.g. /dev/ttyUSB0, COM3): ", validator=URL_VALIDATOR
    )
    return url.strip()


async def run_app(args: argparse.Namespace) -> int:
    """Run PyPlumIO CLI application."""
    url = args.url or await prompt_connection_url()
    output_dir = Path(args.output)
    table = ParameterTable()
    app: Application[None] | None = None

    def on_update(parameters: Sequence[tuple[int, ParameterValues]]) -> None:
        table.update(parameters)
        if app:
            app.invalidate()

    session = Session(
        url=url,
        baudrate=args.baudrate,
        interval=args.interval,
        on_update=on_update,
        on_status=_write_status,
    )
    try:
        product_info = await session.connect()
        if custom_parameters := await load_custom_parameters(product_info):
            comments = _load_comments(
                custom_parameters, output_dir, model_slug(product_info.model)
            )
            for index, description in custom_parameters.descriptions.items():
                table.set_description(
                    index, description, comment=comments.get(index, "")
                )

            table.overrides = tuple(custom_parameters.overrides)

        app, state = create_app(session, table, output_dir, zip_output=args.zip)
        with _capture_logs(state):
            _write_status("Starting interface...")
            await app.run_async()

    except (PyPlumIOError, SerialException, OSError, ValueError) as err:
        sys.stderr.write(f"Error: {_format_error(err)}\n")
        return 1
    finally:
        await session.close()

    return 0


__all__ = (
    "prompt_connection_url",
    "run_app",
)
