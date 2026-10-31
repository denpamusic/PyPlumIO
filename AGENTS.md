# AGENTS.md

Manual for AI agents working on PyPlumIO. Read fully before changing code.

## 1. Project Overview

1.1. PyPlumIO is an asyncio library for communicating with Plum ecoMAX
controllers (and ecoSTER thermostats) over RS-485, via serial port or a
TCP bridge.

1.2. Main consumer is the Home Assistant integration
`homeassistant-plum-ecomax`. Code runs 24/7 on low-power hardware, so
memory efficiency and connection resilience matter.

1.3. Goals: stable public API, strict typing, 100% test coverage, low
complexity, no shortcuts.

1.4. Minimum Python is 3.11. All tools target it. Do not use syntax or
stdlib features newer than 3.11.

1.5. The only source of the version number is `version` in
`pyproject.toml`. Dropping a Python version bumps the minor version.

1.6. `SOFTWARE_VERSION` in `pyplumio/structures/program_version.py` is
packed as three unsigned shorts. It must always be `X.Y.Z` integers.

## 2. Code Style & Engineering Standards

### 2.1. General

2.1.1. Ruff formats and lints: line length 88, double quotes, isort with
`force-sort-within-sections` and `combine-as-imports`.

2.1.2. Each module starts with a module docstring followed by
`from __future__ import annotations`. Add it to every new module.

2.1.3. Logging: module-level `_LOGGER = logging.getLogger(__name__)`.
Use lazy `%s` arguments, never f-strings, in log calls. No `print()`
outside `pyplumio/__main__.py`.

2.1.4. Declare public names in `__all__` at the bottom of the module.

2.1.5. Cognitive complexity must be at most 15 per function
(complexipy). Extract private helpers instead of suppressing.

2.1.6. Use timezone-aware datetimes (Ruff DTZ rules).

### 2.2. Memory: `__slots__`

2.2.1. Every class defines `__slots__`.

2.2.2. Subclasses list only newly added attributes. Use `__slots__ = ()`
if nothing is added.

2.2.3. Declare slot attribute types as class-level annotations, for
example `_data: dict[str, Any]`.

2.2.4. Dataclasses use `@dataclass(slots=True)`, plus `frozen=True`
and/or `kw_only=True` when appropriate.

2.2.5. Exception: a dataclass mixin with fields that is combined with
another slotted base (for example `ThermostatParameterDescription`)
uses plain `@dataclass` with `__slots__ = ()`. Its concrete subclasses
use `slots=True` and generate the slots. Otherwise Python raises
"multiple bases have instance lay-out conflict".

### 2.3. Typing

2.3.1. Annotate every function, including private ones and `-> None`.
Mypy runs with `disallow_untyped_defs`, `disallow_untyped_calls`,
`warn_return_any`, `warn_unreachable` and `strict_equality`. Rules are
relaxed only for `tests.*`.

2.3.2. Use modern syntax: `X | None`, built-in generics (`list[str]`),
`Final` for constants, `TypeAlias`, `@overload` for variant signatures,
`typing.Protocol` for structural types.

2.3.3. `# type: ignore` must include an error code. Unused ignores are
errors.

2.3.4. The package ships `py.typed`, so type signatures are public API.

### 2.4. Docstrings

2.4.1. Ruff `D` rules apply: every module, class, function and method,
including private ones and tests, has a docstring.

2.4.2. The summary line starts on the first line, is in imperative mood
and ends with a period.

2.4.3. Public functions with parameters use Sphinx reST fields:
`:param x:`, `:type x:`, `:return:`, `:rtype:`, `:raise Error:`.
Trivial or private functions may use a one-line docstring.

2.4.4. Sphinx docs in `docs/source` are built from docstrings. Keep
docstrings accurate and update `docs/source/*.rst` when behavior
changes.

### 2.5. Naming

2.5.1. Classes `PascalCase`. Functions, methods and variables
`snake_case`. Private names have a leading underscore.

2.5.2. Constants `SCREAMING_SNAKE_CASE`, annotated with `Final`.

2.5.3. Event and data keys are `ATTR_*` constants (mostly in
`pyplumio/const.py`). Never use raw string literals as event names.

2.5.4. Enums `PascalCase` with `@unique`. Members
`SCREAMING_SNAKE_CASE`.

2.5.5. TypeVars use the `_NameT` form, for example `_EventDataT`.

2.5.6. Event listener methods are named `on_event_<event_name>`.

2.5.7. Frames are named `<Name>Request`, `<Name>Response` and
`<Name>Message`. Structures are named `<Name>Structure`.

2.5.8. Filter implementations are private classes (`_Throttle`) exposed
through public factory functions (`throttle()`).

### 2.6. Errors

2.6.1. Raise exceptions from `pyplumio/exceptions.py` (base
`PyPlumIOError`; wire problems go under `ProtocolError`). Built-in
`ValueError` or `TypeError` are fine for invalid arguments; use
`TypeError` for wrong types (TRY004).

2.6.2. Always chain: `raise SomeError from err` (B904).

2.6.3. Use `contextlib.suppress(...)` instead of `try/except/pass`
(SIM105). Do not catch and immediately re-raise (TRY203).

### 2.7. Async

2.7.1. Never block the event loop.

2.7.2. Keep a reference to every created task (RUF006). Inside
`EventManager` and `TaskManager` subclasses, use `self.create_task()`.

### 2.8. Adding protocol features

2.8.1. New frame checklist: add a `FrameType` member, create the class
decorated with `@frame_handler(FrameType.X)` (and `@contains(*structures)`
for structured responses or messages), add
`@expects_response(ResponseClass)` to requests, put decoding in a
`structures/` module, dispatch results under `ATTR_*` keys, handle them
in the device with `@event_listener`, then add JSON test data and
tests.

2.8.2. Controller firmware varies widely. Decode defensively and do not
assume fixed payload lengths.

## 3. Reactive Event System & Filter Pipeline

3.1. `EventManager` (`pyplumio/helpers/event_manager.py`) is the base of
`Device` and therefore of all devices. It stores the latest value per
event name and notifies subscribers.

3.2. `dispatch(name, value)` awaits callbacks one by one in subscription
order, then stores the value in `data` and sets the event's
`asyncio.Event`.

3.3. Callback contract (an async callable taking the value):
3.3.1. Returning `None` passes the value on unchanged.
3.3.2. Returning any other value replaces it for the following
callbacks and for the stored value.
3.3.3. Returning `StopPropagation` skips the remaining callbacks. The
value is still stored.
3.3.4. Exceptions are logged and swallowed, and the next callback runs.
Do not rely on callback exceptions propagating.

3.4. Consumer API: `get(name, timeout)`, `get_nowait(name, default)`,
`wait_for(name, timeout)`, `subscribe(name, cb)`,
`subscribe_once(name, cb)`, `unsubscribe(name, cb)`,
`dispatch_nowait(name, value)`, `load(data)`.

3.5. `@event_listener` marks a method as a listener. Marked methods are
subscribed automatically in `EventManager.__init__`. Do not subscribe
them manually, and always call `super().__init__()`.
3.5.1. `@event_listener`: the event name comes from the text after
`on_event_` in the method name. The method must follow that naming.
3.5.2. `@event_listener(ATTR_X)`: explicit event name.
3.5.3. `@event_listener(filter=on_change)` (also combinable with a
name): wraps the bound method in a filter at registration. Pass the
filter factory itself, not a call to it.

3.6. Filters (`pyplumio/filters.py`) wrap a callback and return a
callable `Filter`. They can be nested.
3.6.1. `on_change(cb)`: call only when the value differs from the
previous one.
3.6.2. `deadband(cb, tolerance)`: call only when the change exceeds
`tolerance`.
3.6.3. `debounce(cb, min_calls)`: call only after the value stays the
same for `min_calls` dispatches.
3.6.4. `throttle(cb, seconds)`: call at most once per `seconds`.
3.6.5. `delta(cb)`: call with the difference between consecutive values.
3.6.6. `clamp(cb, min_value, max_value, *, ignore_out_of_range=False)`:
clamp the value to the bounds, or drop out-of-range values.
3.6.7. `aggregate(cb, seconds, sample_size)`: call with the sum of
values once `seconds` passes or `sample_size` is reached. Numeric only.
3.6.8. `custom(cb, filter_func)`: call when `filter_func(value)` is
truthy.

3.7. New filters follow the same pattern: a private `__slots__` class
plus a public factory function with a full reST docstring, added to
`__all__`, with tests.

## 4. Testing & Quality Assurance

4.1. Tooling: `uv` manages environments and dependencies, and `prek`
runs git hooks (uv-sync, ruff-check, ruff-format, codespell, mypy,
complexipy).

4.2. Commands:
4.2.1. Setup: `uv sync` and `prek install`.
4.2.2. Tests: `uv run pytest`. Coverage is enforced automatically
through `addopts`.
4.2.3. All checks: `prek run --all-files`.
4.2.4. Docs: `uv run sphinx-build ./docs/source ./docs/build`.

4.3. Before finishing any task, both `uv run pytest` and
`prek run --all-files` must pass.

4.4. Coverage must stay at 100% (line coverage, `--cov-fail-under=100`).
`if TYPE_CHECKING:` and `@overload` are already excluded. Use
`# pragma: no cover` only when coverage is truly impossible.

4.5. `asyncio_mode = "auto"`: write `async def test_...` with no
asyncio markers.

4.6. The `tests/` layout mirrors `pyplumio/`. Use `test_<module>.py`
files and `test_<behavior>` functions, each with a docstring.

4.7. Fixtures in `tests/conftest.py`:
4.7.1. `skip_asyncio_sleep` is autouse and patches `asyncio.sleep`.
Tests never actually sleep.
4.7.2. `frozen_time` (freezegun), `ecomax` (ready EcoMAX instance),
`skip_asyncio_events`.

4.8. Test data comes from real captured frames in
`tests/testdata/{messages,requests,responses,parameters,unknown}/*.json`.
Load it with `load_json_parameters()` for `pytest.mark.parametrize`
(entries need `id`, `message` and `data`), or with the
`@json_test_data` and `@class_from_json` decorators. Prefer adding real
captures over hand-built bytes.

4.9. Mock with `unittest.mock` (`patch`, `AsyncMock`).

4.10. Dependencies: add with `uv add <pkg>` or
`uv add --group <test|lint|typing|docs> <pkg>`. Commit `uv.lock`. Do not
create `requirements*.txt`.

4.11. CI: `test.yml` runs pytest on Python 3.11 to 3.14. `lint.yml` and
`typecheck.yml` run on 3.11. `deploy.yml` publishes to PyPI and creates
a GitHub release on `vX.Y.Z*` tags.

4.12. Commits by AI agents: subject prefixed with `[ai]`, at most 50
characters, ending with a period. An extended body is allowed.
