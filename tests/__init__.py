"""Contains a test suite."""


import importlib
import json
import os
import pathlib
from typing import Final

import pytest

TESTDATA_DIR: Final = "testdata"


def load_and_create_class_instance(module_name: str, class_name: str, **kwargs):
    """Load a class and creates it's instance."""
    return getattr(importlib.import_module(module_name), class_name)(**kwargs)


def try_int(key):
    """Try to convert key to integer or return key unchanged
    on error.
    """
    try:
        return int(key)
    except ValueError:
        return key


def decode_hinted_objects(d):
    """Decode a hinted JSON objects."""
    if "__module__" in d and "__class__" in d:
        module_name = d.pop("__module__")
        class_name = d.pop("__class__")
        return load_and_create_class_instance(module_name, class_name, **d)

    if "__bytearray__" in d:
        return bytearray.fromhex("".join(d["items"]))

    if "__tuple__" in d:
        return tuple(d["items"])

    return {try_int(k): v for k, v in d.items()}


def load_json_test_data(path: str):
    """Load test data from JSON file."""
    abs_path = "/".join([os.path.dirname(__file__), TESTDATA_DIR, path])
    file = pathlib.Path(abs_path)
    with open(file, encoding="utf-8") as fp:
        return json.load(fp, object_hook=decode_hinted_objects)


def load_json_parameters(path: str):
    """Prepare JSON test data for parametrization."""
    test_data = load_json_test_data(path)
    return [pytest.param(x["message"], x["data"], id=x["id"]) for x in test_data]
