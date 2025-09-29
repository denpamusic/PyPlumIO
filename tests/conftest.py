"""Contains fixtures for the test suite."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
import functools
import importlib
import inspect
import json
from math import isclose
import os
import pathlib
from typing import Any, Final, TypeVar
from unittest.mock import AsyncMock, patch

from freezegun import freeze_time
import pytest

from pyplumio.const import ProductType, State
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.parameters import NumericType
from pyplumio.structures.network_info import NetworkInfo
from pyplumio.structures.product_info import ATTR_PRODUCT, ProductInfo

TESTDATA_DIR: Final = "testdata"
UNDEFINED: Final = "undefined"
RAISES: Final = "raises"
DEFAULT_TOLERANCE: Final = 1e-6

T = TypeVar("T")


def _create_class_instance(module_name: str, class_name: str, **kwargs):
    """Create class instance and cache it."""
    return getattr(importlib.import_module(module_name), class_name)(**kwargs)


def _try_int(key: Any) -> Any:
    """Try to convert key to integer or return key unchanged on error."""
    try:
        return int(key)
    except ValueError:
        return key


def _decode_hinted_objects(d: Any) -> Any:
    """Decode a hinted JSON objects."""
    if "__module__" in d and "__class__" in d:
        module_name = d.pop("__module__")
        class_name = d.pop("__class__")
        return _create_class_instance(module_name, class_name, **d)

    if "__bytearray__" in d:
        return bytearray.fromhex("".join(d["items"]))

    if "__tuple__" in d:
        return tuple(d["items"])

    return {_try_int(k): v for k, v in d.items()}


def load_json_test_data(path: str) -> Any:
    """Load test data from JSON file."""
    abs_path = "/".join([os.path.dirname(__file__), TESTDATA_DIR, path])
    file = pathlib.Path(abs_path)
    with open(file, encoding="utf-8") as fp:
        return json.load(fp, object_hook=_decode_hinted_objects)


def load_json_parameters(path: str):
    """Prepare JSON test data for parametrization."""
    test_data = load_json_test_data(path)
    return [pytest.param(x["message"], x["data"], id=x["id"]) for x in test_data]


def _bypass_pytest_argument_inspection(
    wrapper: T, signature: inspect.Signature, argument: str
) -> T:
    """Remove argument from pytest's parameter inspection."""
    replacement = signature.replace(
        parameters=[p for p in signature.parameters.values() if p.name != argument]
    )
    setattr(wrapper, "__signature__", replacement)
    return wrapper


def json_test_data(
    json_path: str,
    selector: str | None = None,
    dataset: int = 0,
    name: str | None = None,
):
    """Pytest decorator to inject JSON test data as a test argument."""
    if not name:
        name = json_path.split("/")[-1].split("\\")[-1].rsplit(".", 1)[0]

    if selector:
        name += f"_{selector}"

    def decorator(test_func):
        @functools.wraps(test_func)
        async def wrapper(*args, **kwargs):
            json_test_data = load_json_test_data(json_path)[dataset]
            kwargs[name] = json_test_data[selector] if selector else json_test_data
            return await test_func(*args, **kwargs)

        return _bypass_pytest_argument_inspection(
            wrapper, inspect.signature(test_func), name
        )

    return decorator


def class_from_json(
    cls: type,
    json_path: str,
    /,
    dataset: int = 0,
    arguments: Sequence | None = None,
    name: str | None = None,
):
    """Pytest decorator to inject JSON test data as a test argument."""
    if not name:
        name = json_path.split("/")[-1].split("\\")[-1].rsplit(".", 1)[0]

    init_args = arguments if arguments else ()

    def decorator(test_func):
        @functools.wraps(test_func)
        async def wrapper(*args, **kwargs):
            json_test_data = load_json_test_data(json_path)[dataset]
            kwargs[name] = cls(**{k: json_test_data[k] for k in init_args})
            return await test_func(*args, **kwargs)

        return _bypass_pytest_argument_inspection(
            wrapper, inspect.signature(test_func), name
        )

    return decorator


def equal_parameter_value(
    a: NumericType | State | None, b: NumericType | State | None
) -> bool:
    """Compare the parameter values."""
    if isinstance(a, float) and isinstance(b, float):
        return isclose(a, b, rel_tol=DEFAULT_TOLERANCE)
    else:
        return True if a == b else False


@pytest.fixture(name="skip_asyncio_events")
def fixture_skip_asyncio_events():
    """Bypass asyncio events."""
    with (
        patch("asyncio.Event.wait", new_callable=AsyncMock),
        patch("asyncio.Event.is_set", return_value=True),
    ):
        yield


@pytest.fixture(autouse=True)
def skip_asyncio_sleep():
    """Skip an asyncio sleep calls."""
    with patch("asyncio.sleep"):
        yield


@pytest.fixture(name="ecomax")
async def fixture_ecomax() -> EcoMAX:
    """Return an ecoMAX object."""
    ecomax = EcoMAX(asyncio.Queue(), network=NetworkInfo())
    product_info = ProductInfo(
        type=ProductType.ECOMAX_P,
        id=90,
        uid="TEST",
        logo=23040,
        image=2816,
        model="ecoMAX 350P2-ZF",
    )
    await ecomax.dispatch(ATTR_PRODUCT, product_info)
    return ecomax


@pytest.fixture(name="frozen_time")
def fixture_frozen_time():
    """Get frozen time."""
    with freeze_time("2012-12-12 12:00:00") as frozen_time:
        yield frozen_time


__all__ = [
    "class_from_json",
    "equal_parameter_value",
    "json_test_data",
    "load_json_parameters",
    "load_json_test_data",
]
