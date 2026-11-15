"""Contains tests for the CLI app module."""

from __future__ import annotations

import argparse
from dataclasses import replace
import logging
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from prompt_toolkit.application import Application, create_app_session
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.shortcuts import PromptSession
from prompt_toolkit.validation import ValidationError
import pytest
from serialx import SerialException

from pyplumio.cli.app import (
    _format_error,
    _load_cli_custom_parameters,
    _load_comments,
    _load_custom_parameters_from_file,
    _StatusLogHandler,
    _write_status,
    prompt_connection_url,
    run_app,
)
from pyplumio.cli.codegen import (
    custom_module_path,
    generate_custom_parameter_module,
    write_zip,
    zip_archive_path,
)
from pyplumio.cli.model import ParameterTable
from pyplumio.cli.session import Session
from pyplumio.cli.state import AppState, AppStep, _save_files
from pyplumio.cli.ui import create_app
from pyplumio.exceptions import ConnectionFailedError, PyPlumIOError
from pyplumio.parameters import ParameterValues
from pyplumio.parameters.custom import CustomParameters
from pyplumio.parameters.ecomax import EcomaxNumberDescription
from tests.cli.conftest import (
    DUMMY_CLASS_NAME,
    DUMMY_COMMENTS,
    DUMMY_ID,
    DUMMY_MODEL,
    DUMMY_SLUG,
    EcoMAX999TEST,
    app_step,
    dummy_product_info,
    write_dummy_custom_module,
)


async def test_prompt_connection_url_tcp() -> None:
    """Test prompting for TCP connection URL."""
    mock_session = MagicMock(spec=PromptSession)
    mock_session.prompt_async = AsyncMock(side_effect=["tcp", "192.168.1.50", "8899"])

    url = await prompt_connection_url(mock_session)
    assert url == "socket://192.168.1.50:8899"

    # Verify validators passed
    calls = mock_session.prompt_async.call_args_list
    type_validator = calls[0].kwargs["validator"]
    type_validator.validate(Document("tcp"))
    type_validator.validate(Document("SERIAL"))
    with pytest.raises(ValidationError):
        type_validator.validate(Document("invalid"))

    host_validator = calls[1].kwargs["validator"]
    host_validator.validate(Document("localhost"))
    with pytest.raises(ValidationError):
        host_validator.validate(Document(""))

    port_validator = calls[2].kwargs["validator"]
    port_validator.validate(Document("8899"))
    port_validator.validate(Document(""))
    with pytest.raises(ValidationError):
        port_validator.validate(Document("0"))
    with pytest.raises(ValidationError):
        port_validator.validate(Document("70000"))
    with pytest.raises(ValidationError):
        port_validator.validate(Document("abc"))


async def test_prompt_connection_url_tcp_default_port() -> None:
    """Test prompting for TCP connection URL with default port."""
    mock_session = MagicMock(spec=PromptSession)
    mock_session.prompt_async = AsyncMock(side_effect=["tcp", "localhost", ""])

    url = await prompt_connection_url(mock_session)
    assert url == "socket://localhost:8899"


async def test_prompt_connection_url_serial() -> None:
    """Test prompting for serial connection URL."""
    mock_session = MagicMock(spec=PromptSession)
    mock_session.prompt_async = AsyncMock(side_effect=["serial", "COM3"])

    url = await prompt_connection_url(mock_session)
    assert url == "COM3"

    url_validator = mock_session.prompt_async.call_args_list[1].kwargs["validator"]
    url_validator.validate(Document("/dev/ttyUSB0"))
    with pytest.raises(ValidationError):
        url_validator.validate(Document(""))


async def test_prompt_connection_url_default_session() -> None:
    """Test prompting for connection URL creates a default PromptSession."""
    mock_session = MagicMock(spec=PromptSession)
    mock_session.prompt_async = AsyncMock(side_effect=["serial", "COM3"])

    with patch("pyplumio.cli.app.PromptSession", return_value=mock_session) as mock_cls:
        url = await prompt_connection_url()

    mock_cls.assert_called_once_with()
    assert url == "COM3"


def test_status_log_handler() -> None:
    """Test _StatusLogHandler routing warning logs to app status."""
    session = Session(url="socket://localhost:8899")
    table = ParameterTable()
    state = AppState(session, table, Path.cwd())
    mock_app = MagicMock(spec=Application)
    state.application = mock_app

    handler = _StatusLogHandler(state)
    logger = logging.getLogger("test_status_logger")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    logger.debug("Debug message ignored")
    assert state.status == ""
    mock_app.invalidate.assert_not_called()

    logger.warning("Warning message captured")
    assert state.status == "Warning message captured"
    mock_app.invalidate.assert_called_once()


async def test_run_app(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test run_app main loop execution."""
    args = argparse.Namespace(
        url="socket://localhost:8899",
        output=str(tmp_path),
        interval=1.0,
        baudrate=115200,
        zip=False,
    )

    product_info = dummy_product_info()
    source_path = write_dummy_custom_module(tmp_path / "source")

    created_sessions: list[Session] = []
    created_states: list[AppState] = []
    orig_init = Session.__init__
    orig_create_app = create_app

    def track_init(self: Session, *a: Any, **kw: Any) -> None:
        orig_init(self, *a, **kw)
        created_sessions.append(self)

    def track_create_app(*a: Any, **kw: Any) -> tuple[Application[None], AppState]:
        app, state = orig_create_app(*a, **kw)
        created_states.append(state)
        return app, state

    with (
        create_pipe_input() as pipe_input,
        create_app_session(input=pipe_input, output=DummyOutput()),
        patch.object(Session, "__init__", track_init),
        patch("pyplumio.cli.app.create_app", side_effect=track_create_app),
        patch(
            "pyplumio.cli.app.load_custom_parameters",
            new_callable=AsyncMock,
            return_value=EcoMAX999TEST(),
        ),
        patch(
            "pyplumio.cli.app.inspect.getsourcefile",
            return_value=str(source_path),
        ),
        patch(
            "pyplumio.cli.session.Session.connect", new_callable=AsyncMock
        ) as mock_connect,
        patch(
            "prompt_toolkit.application.Application.run_async",
            new_callable=AsyncMock,
        ) as mock_run,
        patch(
            "pyplumio.cli.session.Session.close", new_callable=AsyncMock
        ) as mock_close,
        patch("pyplumio.cli.session.Session._reconnect", new_callable=AsyncMock),
    ):

        async def fake_run_async(*_args: Any, **_kwargs: Any) -> None:
            if created_sessions:
                sess = created_sessions[0]
                if sess._on_update:
                    sess._on_update(
                        [(0, ParameterValues(value=10, min_value=0, max_value=20))]
                    )

                await sess._handle_disconnect()

        mock_connect.return_value = product_info
        mock_run.side_effect = fake_run_async

        ret = await run_app(args)
        assert ret == 0
        mock_connect.assert_awaited_once()
        mock_run.assert_awaited_once()
        mock_close.assert_awaited_once()
        assert created_sessions[0]._on_status is _write_status
        assert created_states[0].table.descriptions == EcoMAX999TEST.descriptions
        assert created_states[0].table.overrides == EcoMAX999TEST.overrides
        assert created_states[0].table.comments == DUMMY_COMMENTS
        captured = capsys.readouterr()
        assert "Starting interface...\n" in captured.err


async def test_run_app_error(capsys: pytest.CaptureFixture[str]) -> None:
    """Test run_app handling connection error."""
    args = argparse.Namespace(
        url="socket://localhost:8899",
        output="output",
        interval=1.0,
        baudrate=115200,
        zip=False,
    )

    with patch(
        "pyplumio.cli.session.Session.connect",
        side_effect=PyPlumIOError("Connection refused"),
    ):
        ret = await run_app(args)
        assert ret == 1
        captured = capsys.readouterr()
        assert "Error: Connection refused" in captured.err

    with patch(
        "pyplumio.cli.session.Session.connect",
        side_effect=SerialException("No handler registered"),
    ):
        ret = await run_app(args)
        assert ret == 1
        captured = capsys.readouterr()
        assert "Error: No handler registered" in captured.err

    with patch(
        "pyplumio.cli.session.Session.connect",
        side_effect=PyPlumIOError(
            f"{DUMMY_MODEL} did not return service parameters after 3 attempts; "
            "this controller may not support them"
        ),
    ):
        ret = await run_app(args)
        assert ret == 1
        captured = capsys.readouterr()
        assert (
            f"Error: {DUMMY_MODEL} did not return service parameters "
            "after 3 attempts; this controller may not support them\n" in captured.err
        )


def test_write_status(capsys: pytest.CaptureFixture[str]) -> None:
    """Test _write_status writes to standard error and flushes."""
    _write_status("Testing status message")
    captured = capsys.readouterr()
    assert captured.err == "Testing status message\n"


def test_format_error() -> None:
    """Test _format_error formatting with and without message or cause."""
    assert _format_error(PyPlumIOError("explicit")) == "explicit"
    assert _format_error(ConnectionFailedError()) == "ConnectionFailedError"

    try:
        try:
            raise OSError("timed out")
        except OSError as err:
            raise ConnectionFailedError from err
    except ConnectionFailedError as wrapped:
        assert _format_error(wrapped) == "ConnectionFailedError: timed out"


async def test_run_app_disconnect_status(tmp_path: Path) -> None:
    """Test run_app disconnect callback sets status and invalidates app."""
    args = argparse.Namespace(
        url="socket://localhost:8899",
        output=str(tmp_path),
        interval=1.0,
        baudrate=115200,
        zip=False,
    )
    product_info = dummy_product_info()
    created_sessions: list[Session] = []
    created_states: list[AppState] = []
    orig_init = Session.__init__
    orig_create_app = create_app

    def track_init(self: Session, *a: Any, **kw: Any) -> None:
        orig_init(self, *a, **kw)
        created_sessions.append(self)

    def track_create_app(*a: Any, **kw: Any) -> tuple[Application[None], AppState]:
        app, state = orig_create_app(*a, **kw)
        created_states.append(state)
        return app, state

    with (
        create_pipe_input() as pipe_input,
        create_app_session(input=pipe_input, output=DummyOutput()),
        patch.object(Session, "__init__", track_init),
        patch("pyplumio.cli.app.create_app", side_effect=track_create_app),
        patch(
            "pyplumio.cli.session.Session.connect", new_callable=AsyncMock
        ) as mock_connect,
        patch(
            "prompt_toolkit.application.Application.run_async",
            new_callable=AsyncMock,
        ) as mock_run,
        patch(
            "pyplumio.cli.session.Session.close", new_callable=AsyncMock
        ) as mock_close,
        patch("pyplumio.cli.session.Session._reconnect", new_callable=AsyncMock),
    ):

        async def fake_run_async(*_args: Any, **_kwargs: Any) -> None:
            sess = created_sessions[0]
            sess.product_info = product_info
            sess.last_frame_message = b"\x00" * 40
            sess.last_parameters = [
                (0, ParameterValues(value=10, min_value=0, max_value=20))
            ]
            if sess._on_update:
                sess._on_update(
                    [(0, ParameterValues(value=10, min_value=0, max_value=20))]
                )

            created_states[0].table.set_description(
                0, EcomaxNumberDescription(name="boiler_temp")
            )
            await sess._handle_disconnect()

        mock_connect.return_value = product_info
        mock_run.side_effect = fake_run_async

        ret = await run_app(args)
        assert ret == 0
        mock_close.assert_awaited_once()
        state = created_states[0]
        assert state.status == (
            "Connection lost. Reconnecting in background in 5 seconds..."
        )
        _save_files(state)
        assert state.status == f"Files saved to {tmp_path}."


async def test_run_app_zip_flag(tmp_path: Path) -> None:
    """Test run_app forwards args.zip to create_app."""
    args = argparse.Namespace(
        url="socket://localhost:8899",
        output=str(tmp_path),
        interval=1.0,
        baudrate=115200,
        zip=True,
    )
    product_info = dummy_product_info()
    created_states: list[AppState] = []
    orig_create_app = create_app

    def track_create_app(*a: Any, **kw: Any) -> tuple[Application[None], AppState]:
        app, state = orig_create_app(*a, **kw)
        created_states.append(state)
        return app, state

    with (
        create_pipe_input() as pipe_input,
        create_app_session(input=pipe_input, output=DummyOutput()),
        patch("pyplumio.cli.app.create_app", side_effect=track_create_app),
        patch(
            "pyplumio.cli.session.Session.connect", new_callable=AsyncMock
        ) as mock_connect,
        patch(
            "prompt_toolkit.application.Application.run_async",
            new_callable=AsyncMock,
        ),
        patch("pyplumio.cli.session.Session.close", new_callable=AsyncMock),
    ):
        mock_connect.return_value = product_info
        ret = await run_app(args)
        assert ret == 0
        assert len(created_states) == 1
        assert bool(created_states[0].zip_output) is True


def test_load_comments(tmp_path: Path) -> None:
    """Test _load_comments precedence, source fallback, and missing source."""
    module_path = custom_module_path(tmp_path, DUMMY_SLUG)
    module_path.parent.mkdir(parents=True, exist_ok=True)
    module_path.write_text(
        "        # custom output comment\n"
        '        4: EcomaxNumberDescription(name="fuel_type"),\n',
        encoding="utf-8",
    )
    assert _load_comments(EcoMAX999TEST(), tmp_path, DUMMY_SLUG) == {
        4: "custom output comment"
    }

    source_path = write_dummy_custom_module(tmp_path / "source")
    with patch("pyplumio.cli.app.inspect.getsourcefile", return_value=str(source_path)):
        assert (
            _load_comments(EcoMAX999TEST(), tmp_path / "empty", DUMMY_SLUG)
            == DUMMY_COMMENTS
        )
        assert (
            _load_comments(EcoMAX999TEST(), tmp_path, DUMMY_SLUG, prefer_output=False)
            == DUMMY_COMMENTS
        )

    with patch("pyplumio.cli.app.inspect.getsourcefile", return_value=None):
        assert _load_comments(EcoMAX999TEST(), tmp_path / "empty", DUMMY_SLUG) == {}

    dynamic_instance = _load_custom_parameters_from_file(
        source_path, dummy_product_info()
    )
    assert (
        _load_comments(dynamic_instance, tmp_path, DUMMY_SLUG, prefer_output=False)
        == {}
    )

    with patch.object(Path, "read_text", side_effect=OSError("Permission denied")):
        assert _load_comments(EcoMAX999TEST(), tmp_path, DUMMY_SLUG) == {}


async def test_loaded_comments_prefill_and_preserve_on_save(tmp_path: Path) -> None:
    """Test loaded comments are pre-filled at comment step and preserved on save."""
    product_info = dummy_product_info()
    existing_module = custom_module_path(tmp_path, DUMMY_SLUG)
    existing_module.parent.mkdir(parents=True, exist_ok=True)
    existing_module.write_text(
        generate_custom_parameter_module(
            product_info,
            {
                0: EcoMAX999TEST.descriptions[0],
                4: EcoMAX999TEST.descriptions[4],
            },
            EcoMAX999TEST.overrides,
            comments={0: "untouched output comment", 4: "0 - pellets, 1 - wood"},
        ),
        encoding="utf-8",
    )

    args = argparse.Namespace(
        url="socket://localhost:8899",
        output=str(tmp_path),
        interval=1.0,
        baudrate=115200,
        zip=False,
    )
    created_sessions: list[Session] = []
    created_states: list[AppState] = []
    orig_init = Session.__init__
    orig_create_app = create_app

    def track_init(self: Session, *a: Any, **kw: Any) -> None:
        orig_init(self, *a, **kw)
        created_sessions.append(self)

    def track_create_app(*a: Any, **kw: Any) -> tuple[Application[None], AppState]:
        app, state = orig_create_app(*a, **kw)
        created_states.append(state)
        return app, state

    async def fake_run_async(*_args: Any, **_kwargs: Any) -> None:
        sess = created_sessions[0]
        sess.product_info = product_info
        sess.last_frame_message = b"\x00" * 40
        sess.last_parameters = [
            (0, ParameterValues(value=10, min_value=0, max_value=20)),
            (4, ParameterValues(value=0, min_value=0, max_value=1)),
        ]
        if sess._on_update:
            sess._on_update(sess.last_parameters)

        state = created_states[0]
        assert state.status == f"Loaded custom parameters from {tmp_path}."
        assert state.table.overrides == EcoMAX999TEST.overrides
        buff = Buffer()

        # Edit index 4 and verify loaded comment is pre-filled
        buff.text = "4"
        for _ in range(6):
            state.dispatch_enter(buff)  # select 4 and keep name/type/offset/step/unit

        assert app_step(state) == AppStep.COMMENT
        assert buff.text == "0 - pellets, 1 - wood"
        state.dispatch_enter(buff)  # keep pre-filled comment
        buff.text = "y"
        state.dispatch_enter(buff)

        # Save to output_dir without touching index 0 and verify both comments persist
        state.start_save(buff, save_as_zip=False)
        assert app_step(state) == AppStep.OVERWRITE
        assert state.prompt == f"Overwrite existing {DUMMY_SLUG}.py? [y/N]: "
        buff.text = "y"
        state.dispatch_enter(buff)

    with (
        create_pipe_input() as pipe_input,
        create_app_session(input=pipe_input, output=DummyOutput()),
        patch.object(Session, "__init__", track_init),
        patch("pyplumio.cli.app.create_app", side_effect=track_create_app),
        patch(
            "pyplumio.cli.app.load_custom_parameters",
            new_callable=AsyncMock,
        ) as mock_load_builtin,
        patch(
            "pyplumio.cli.session.Session.connect",
            new_callable=AsyncMock,
            return_value=product_info,
        ),
        patch(
            "prompt_toolkit.application.Application.run_async",
            new_callable=AsyncMock,
            side_effect=fake_run_async,
        ),
        patch("pyplumio.cli.session.Session.close", new_callable=AsyncMock),
    ):
        assert await run_app(args) == 0
        mock_load_builtin.assert_not_awaited()

    saved_module = existing_module.read_text(encoding="utf-8")
    assert "        # untouched output comment\n        0: " in saved_module
    assert "        # 0 - pellets, 1 - wood\n        4: " in saved_module


def test_load_custom_parameters_from_file(tmp_path: Path) -> None:
    """Test _load_custom_parameters_from_file validation and error cases."""
    product_info = dummy_product_info()
    valid_path = write_dummy_custom_module(tmp_path / "valid")
    loaded = _load_custom_parameters_from_file(valid_path, product_info)
    assert isinstance(loaded, CustomParameters)
    assert loaded.validate(product_info)
    assert loaded.descriptions == EcoMAX999TEST.descriptions

    invalid_suffix = tmp_path / "invalid.txt"
    invalid_suffix.write_text("", encoding="utf-8")
    with pytest.raises(ImportError, match="Could not create module spec"):
        _load_custom_parameters_from_file(invalid_suffix, product_info)

    missing_class = tmp_path / "missing.py"
    missing_class.write_text("VALUE = 1\n", encoding="utf-8")
    with pytest.raises(AttributeError):
        _load_custom_parameters_from_file(missing_class, product_info)

    wrong_class = tmp_path / "wrong.py"
    wrong_class.write_text(f"class {DUMMY_CLASS_NAME}:\n    pass\n", encoding="utf-8")
    with pytest.raises(TypeError, match="Expected instance of 'CustomParameters'"):
        _load_custom_parameters_from_file(wrong_class, product_info)

    non_callable = tmp_path / "non_callable.py"
    non_callable.write_text(f"{DUMMY_CLASS_NAME} = 123\n", encoding="utf-8")
    with pytest.raises(TypeError):
        _load_custom_parameters_from_file(non_callable, product_info)

    missing_signature = tmp_path / "missing_signature.py"
    missing_signature.write_text(
        "from pyplumio.parameters.custom import CustomParameters\n"
        f"class {DUMMY_CLASS_NAME}(CustomParameters):\n"
        "    pass\n",
        encoding="utf-8",
    )
    with pytest.raises(AttributeError):
        _load_custom_parameters_from_file(missing_signature, product_info)

    with pytest.raises(ValueError, match="Signature mismatch"):
        _load_custom_parameters_from_file(
            valid_path, replace(product_info, id=DUMMY_ID + 1)
        )

    wrong_model = tmp_path / "wrong_model.py"
    wrong_model.write_text(
        "from pyplumio.parameters.custom import CustomParameters, Signature\n"
        f"class {DUMMY_CLASS_NAME}(CustomParameters):\n"
        f'    signature = Signature(model="ecoMAX 999-OTHER", id={DUMMY_ID})\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Signature mismatch"):
        _load_custom_parameters_from_file(wrong_model, product_info)


async def test_load_cli_custom_parameters_fallback(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test _load_cli_custom_parameters precedence, fallback, and warnings."""
    product_info = dummy_product_info()

    missing_dir = tmp_path / "missing"
    with (
        caplog.at_level(logging.WARNING),
        patch(
            "pyplumio.cli.app.load_custom_parameters",
            new_callable=AsyncMock,
            return_value=EcoMAX999TEST(),
        ) as mock_load,
    ):
        params, status, from_output = await _load_cli_custom_parameters(
            missing_dir, product_info
        )

    assert isinstance(params, EcoMAX999TEST)
    assert status == ""
    assert from_output is False
    assert caplog.text == ""
    assert capsys.readouterr().err == ""
    mock_load.assert_awaited_once_with(product_info)

    broken_dir = tmp_path / "broken"
    broken_path = custom_module_path(broken_dir, DUMMY_SLUG)
    broken_path.parent.mkdir(parents=True, exist_ok=True)
    broken_path.write_text("def broken(:\n", encoding="utf-8")
    with (
        caplog.at_level(logging.WARNING),
        patch(
            "pyplumio.cli.app.load_custom_parameters",
            new_callable=AsyncMock,
            return_value=EcoMAX999TEST(),
        ) as mock_load,
    ):
        params, status, from_output = await _load_cli_custom_parameters(
            broken_dir, product_info
        )

    assert isinstance(params, EcoMAX999TEST)
    assert from_output is False
    assert status.startswith(
        f"Warning: Failed to load custom parameters from {broken_path}:"
    )
    assert "Falling back to built-in definitions." in status
    assert "Failed to load custom parameters from" in caplog.text
    assert f"{status}\n" in capsys.readouterr().err
    mock_load.assert_awaited_once_with(product_info)

    valid_dir = tmp_path / "valid"
    write_dummy_custom_module(valid_dir)
    with patch(
        "pyplumio.cli.app.load_custom_parameters",
        new_callable=AsyncMock,
    ) as mock_load:
        params, status, from_output = await _load_cli_custom_parameters(
            valid_dir, product_info
        )

    assert isinstance(params, CustomParameters)
    assert status == f"Loaded custom parameters from {valid_dir}."
    assert from_output is True
    assert f"{status}\n" in capsys.readouterr().err
    mock_load.assert_not_awaited()


async def test_load_cli_custom_parameters_zip_and_empty_error(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test _load_cli_custom_parameters ignores zip archives and empty errors."""
    product_info = dummy_product_info()
    zip_only_dir = tmp_path / "zip_only"
    zip_module_path = custom_module_path(zip_only_dir, DUMMY_SLUG)
    write_zip(
        zip_archive_path(zip_only_dir, DUMMY_SLUG),
        {
            zip_module_path: generate_custom_parameter_module(
                product_info,
                EcoMAX999TEST.descriptions,
                EcoMAX999TEST.overrides,
            )
        },
        zip_only_dir,
    )
    with (
        caplog.at_level(logging.WARNING),
        patch(
            "pyplumio.cli.app.load_custom_parameters",
            new_callable=AsyncMock,
            return_value=EcoMAX999TEST(),
        ) as mock_load,
    ):
        params, status, from_output = await _load_cli_custom_parameters(
            zip_only_dir, product_info
        )

    assert isinstance(params, EcoMAX999TEST)
    assert status == ""
    assert from_output is False
    assert caplog.text == ""
    assert capsys.readouterr().err == ""
    mock_load.assert_awaited_once_with(product_info)

    empty_err_dir = tmp_path / "empty_err"
    empty_err_path = custom_module_path(empty_err_dir, DUMMY_SLUG)
    empty_err_path.parent.mkdir(parents=True, exist_ok=True)
    empty_err_path.write_text("raise ValueError()\n", encoding="utf-8")
    with (
        caplog.at_level(logging.WARNING),
        patch(
            "pyplumio.cli.app.load_custom_parameters",
            new_callable=AsyncMock,
            return_value=None,
        ) as mock_load,
    ):
        params, status, from_output = await _load_cli_custom_parameters(
            empty_err_dir, product_info
        )

    assert params is None
    assert from_output is False
    assert status == (
        f"Warning: Failed to load custom parameters from {empty_err_path}: "
        "ValueError. Falling back to built-in definitions."
    )
    assert f"{status}\n" in capsys.readouterr().err
    mock_load.assert_awaited_once_with(product_info)


async def test_run_app_invalid_output_module_fallback(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test run_app falls back cleanly when output module fails validation."""
    product_info = dummy_product_info()
    mismatched_info = replace(product_info, id=DUMMY_ID + 1)
    rejected_path = custom_module_path(tmp_path, DUMMY_SLUG)
    rejected_path.parent.mkdir(parents=True, exist_ok=True)
    rejected_path.write_text(
        generate_custom_parameter_module(
            mismatched_info,
            {4: EcoMAX999TEST.descriptions[4]},
            comments={4: "rejected output comment"},
        ),
        encoding="utf-8",
    )
    source_path = write_dummy_custom_module(tmp_path / "source")

    args = argparse.Namespace(
        url="socket://localhost:8899",
        output=str(tmp_path),
        interval=1.0,
        baudrate=115200,
        zip=False,
    )
    created_states: list[AppState] = []
    orig_create_app = create_app

    def track_create_app(*a: Any, **kw: Any) -> tuple[Application[None], AppState]:
        app, state = orig_create_app(*a, **kw)
        created_states.append(state)
        return app, state

    async def fake_run_async(*_args: Any, **_kwargs: Any) -> None:
        state = created_states[0]
        assert state.status.startswith(
            f"Warning: Failed to load custom parameters from {rejected_path}:"
        )
        assert state.table.comments == DUMMY_COMMENTS

    with (
        caplog.at_level(logging.WARNING),
        create_pipe_input() as pipe_input,
        create_app_session(input=pipe_input, output=DummyOutput()),
        patch("pyplumio.cli.app.create_app", side_effect=track_create_app),
        patch(
            "pyplumio.cli.app.load_custom_parameters",
            new_callable=AsyncMock,
            return_value=EcoMAX999TEST(),
        ) as mock_load,
        patch(
            "pyplumio.cli.app.inspect.getsourcefile",
            return_value=str(source_path),
        ),
        patch(
            "pyplumio.cli.session.Session.connect",
            new_callable=AsyncMock,
            return_value=product_info,
        ),
        patch(
            "prompt_toolkit.application.Application.run_async",
            new_callable=AsyncMock,
            side_effect=fake_run_async,
        ),
        patch("pyplumio.cli.session.Session.close", new_callable=AsyncMock),
    ):
        assert await run_app(args) == 0
        mock_load.assert_awaited_once_with(product_info)

    assert "Failed to load custom parameters from" in caplog.text
    assert f"Warning: Failed to load custom parameters from {rejected_path}:" in (
        capsys.readouterr().err
    )
