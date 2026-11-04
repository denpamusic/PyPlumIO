"""Contains tests for the CLI codegen module."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from pyplumio.cli.codegen import (
    generate_all_files,
    generate_custom_parameter_module,
    generate_test_module,
    write_files,
)
from pyplumio.const import PERCENTAGE, ProductType, UnitOfMeasurement
from pyplumio.frames.responses import EcomaxServiceParametersResponse
from pyplumio.parameters import ParameterValues
from pyplumio.parameters.custom import ParameterOverride
from pyplumio.parameters.custom.ecomax_350p2_zf import EcoMAX350P2ZF
from pyplumio.parameters.ecomax import EcomaxNumberDescription, EcomaxSwitchDescription
from pyplumio.structures.ecomax_service_parameters import ATTR_ECOMAX_SERVICE_PARAMETERS
from pyplumio.structures.product_info import ProductInfo


def test_codegen_golden(tmp_path: Path) -> None:
    """Test codegen golden test with ecoMAX 350P2-ZF test data."""
    json_path = (
        Path(__file__).parent.parent
        / "testdata"
        / "parameters"
        / "ecomax_350p2_zf.json"
    )
    raw_json = json.loads(json_path.read_text(encoding="utf-8"))
    raw_bytes = bytes.fromhex("".join(raw_json[0]["message"]["items"]))

    resp = EcomaxServiceParametersResponse(message=raw_bytes)
    frame_parameters = resp.data[ATTR_ECOMAX_SERVICE_PARAMETERS]

    product_info = ProductInfo(
        type=ProductType.ECOMAX_P,
        id=90,
        uid="*TEST*",
        logo=0,
        image=0,
        model="ecoMAX 350P2-ZF",
    )

    files = generate_all_files(
        product_info=product_info,
        descriptions=EcoMAX350P2ZF.descriptions,
        overrides=getattr(EcoMAX350P2ZF, "overrides", ()),
        frame_message=raw_bytes,
        frame_parameters=frame_parameters,
        output_dir=tmp_path,
    )

    # 1. Assert JSON round-trips
    json_content = files[
        tmp_path / "tests" / "testdata" / "parameters" / "ecomax_350p2_zf.json"
    ]
    parsed_json = json.loads(json_content)
    roundtrip_bytes = bytes.fromhex("".join(parsed_json[0]["message"]["items"]))
    assert roundtrip_bytes == raw_bytes

    # 2. Assert generated module compiles and matches signature and descriptions
    mod_content = files[
        tmp_path / "pyplumio" / "parameters" / "custom" / "ecomax_350p2_zf.py"
    ]
    code_obj = compile(mod_content, "<ecomax_350p2_zf>", "exec")
    local_ns: dict[str, object] = {}
    exec(code_obj, local_ns)  # noqa: S102
    gen_cls = local_ns["EcoMAX350P2ZF"]
    assert getattr(gen_cls, "signature") == EcoMAX350P2ZF.signature
    assert getattr(gen_cls, "descriptions") == EcoMAX350P2ZF.descriptions

    # 3. Assert test module compiles
    test_content = files[
        tmp_path / "tests" / "parameters" / "custom" / "test_ecomax_350p2_zf.py"
    ]
    compile(test_content, "<test_ecomax_350p2_zf>", "exec")

    # 4. Write files and run ruff on them
    write_files(files)
    for p in files:
        assert p.is_file()

    pytest.importorskip("ruff")
    root_dir = Path(__file__).parent.parent.parent
    pyproject_path = str(root_dir / "pyproject.toml")
    tests_ruff_path = str(root_dir / "tests" / "ruff.toml")

    # Ruff check on generated custom parameter module
    mod_path = tmp_path / "pyplumio" / "parameters" / "custom" / "ecomax_350p2_zf.py"
    res_mod_check = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "--config",
            pyproject_path,
            str(mod_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res_mod_check.returncode == 0, res_mod_check.stdout + res_mod_check.stderr

    # Ruff check on generated test file
    test_path = tmp_path / "tests" / "parameters" / "custom" / "test_ecomax_350p2_zf.py"
    res_test_check = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "--config",
            tests_ruff_path,
            str(test_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res_test_check.returncode == 0, res_test_check.stdout + res_test_check.stderr

    res_format = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "format",
            "--config",
            pyproject_path,
            "--check",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res_format.returncode == 0, res_format.stdout + res_format.stderr


def test_codegen_with_overrides_and_switches() -> None:
    """Test codegen with parameter overrides and switch descriptions."""
    product_info = ProductInfo(
        type=ProductType.ECOMAX_I,
        id=12,
        uid="*TEST*",
        logo=0,
        image=0,
        model="ecoMAX 860P",
    )
    replacement = EcomaxNumberDescription(
        name="long_replacement_parameter_name",
        step=5,
        offset=-10,
        unit_of_measurement=PERCENTAGE,
    )
    overrides = [
        # Short override: fits on one line
        ParameterOverride(
            original="a",
            replacement=EcomaxNumberDescription(name="a"),
        ),
        # Medium override: replacement fits on one line inside
        # multiline ParameterOverride
        ParameterOverride(
            original="medium_param_name",
            replacement=EcomaxSwitchDescription(name="bar"),
        ),
        # Long override: replacement itself needs multiline formatting
        ParameterOverride(
            original="original_long_parameter_name_to_wrap",
            replacement=replacement,
        ),
    ]
    descriptions = {
        0: EcomaxSwitchDescription(name="power_switch"),
        1: EcomaxNumberDescription(
            name="boiler_temp",
            step=1,
            offset=0,
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        2: EcomaxNumberDescription(
            name="a_very_long_parameter_name_that_forces_multi_line_wrapping_in_test_row",
            step=1,
            offset=0,
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
    }

    mod_str = generate_custom_parameter_module(product_info, descriptions, overrides)
    assert "class EcoMAX860P(CustomParameters):" in mod_str
    assert "ParameterOverride(" in mod_str
    assert "descriptions = {" in mod_str
    assert "power_switch" in mod_str

    # Test test module generation with switches and multiline rows
    test_str = generate_test_module(
        product_info,
        descriptions,
        [
            (0, ParameterValues(value=1, min_value=0, max_value=1)),
            (1, ParameterValues(value=50, min_value=20, max_value=80)),
            (2, ParameterValues(value=50, min_value=20, max_value=80)),
        ],
    )
    assert "STATE_ON" in test_str
    assert "STATE_OFF" in test_str
    assert '("power_switch", STATE_ON, STATE_OFF, STATE_ON, None)' in test_str
    assert (
        "a_very_long_parameter_name_that_forces_multi_line_wrapping_in_test_row"
        in test_str
    )
