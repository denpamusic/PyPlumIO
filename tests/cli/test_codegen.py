"""Contains tests for the CLI codegen module."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import sys

import pytest

from pyplumio.cli.codegen import (
    _format_field_value,
    generate_all_files,
    generate_custom_parameter_module,
    generate_test_module,
    write_files,
)
from pyplumio.const import PERCENTAGE, ProductType, UnitOfMeasurement
from pyplumio.frames.responses import EcomaxServiceParametersResponse
from pyplumio.parameters import ParameterDescription, ParameterValues
from pyplumio.parameters.custom import ParameterOverride
from pyplumio.parameters.custom.ecomax_350p2_zf import EcoMAX350P2ZF
from pyplumio.parameters.ecomax import EcomaxNumberDescription, EcomaxSwitchDescription
from pyplumio.parameters.mixer import MixerNumberDescription
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

    response = EcomaxServiceParametersResponse(message=raw_bytes)
    frame_parameters = response.data[ATTR_ECOMAX_SERVICE_PARAMETERS]

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
    module_content = files[
        tmp_path / "pyplumio" / "parameters" / "custom" / "ecomax_350p2_zf.py"
    ]
    code_obj = compile(module_content, "<ecomax_350p2_zf>", "exec")
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
    for file_path in files:
        assert file_path.is_file()

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


def test_codegen_non_default_fields_roundtrip(tmp_path: Path) -> None:
    """Test round-tripping non-default fields: optimistic, precision, and offset."""
    product_info = ProductInfo(
        type=ProductType.ECOMAX_P,
        id=42,
        uid="*TEST*",
        logo=0,
        image=0,
        model="ecoMAX 860P",
    )
    descriptions = {
        0: EcomaxNumberDescription(
            name="detailed_temp",
            step=0.5,
            offset=-10,
            precision=2,
            optimistic=True,
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        1: EcomaxSwitchDescription(
            name="fast_switch",
            optimistic=True,
        ),
    }
    overrides = [
        ParameterOverride(
            original="mixer_temp",
            replacement=MixerNumberDescription(name="mixer_temp", step=1, offset=5),
        )
    ]
    frame_parameters = [
        (0, ParameterValues(value=20, min_value=0, max_value=100)),
        (1, ParameterValues(value=1, min_value=0, max_value=1)),
    ]

    files = generate_all_files(
        product_info=product_info,
        descriptions=descriptions,
        overrides=overrides,
        frame_message=b"\x00" * 40,
        frame_parameters=frame_parameters,
        output_dir=tmp_path,
    )

    module_content = files[
        tmp_path / "pyplumio" / "parameters" / "custom" / "ecomax_860p.py"
    ]
    assert "optimistic=True" in module_content
    assert "precision=2" in module_content
    assert "offset=-10" in module_content
    assert (
        "from pyplumio.parameters.mixer import MixerNumberDescription" in module_content
    )

    # Exec module and verify exact dataclass equality
    code_obj = compile(module_content, "<ecomax_860p>", "exec")
    local_ns: dict[str, object] = {}
    exec(code_obj, local_ns)  # noqa: S102
    generated_class = local_ns["EcoMAX860P"]
    assert getattr(generated_class, "descriptions") == descriptions
    assert getattr(generated_class, "overrides") == tuple(overrides)

    write_files(files)
    pytest.importorskip("ruff")
    root_dir = Path(__file__).parent.parent.parent
    pyproject_path = str(root_dir / "pyproject.toml")
    tests_ruff_path = str(root_dir / "tests" / "ruff.toml")

    mod_path = tmp_path / "pyplumio" / "parameters" / "custom" / "ecomax_860p.py"
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

    test_path = tmp_path / "tests" / "parameters" / "custom" / "test_ecomax_860p.py"
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
        ParameterOverride(
            original="a",
            replacement=EcomaxNumberDescription(name="a"),
        ),
        ParameterOverride(
            original="medium_param_name",
            replacement=EcomaxSwitchDescription(name="bar"),
        ),
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

    module_content = generate_custom_parameter_module(
        product_info, descriptions, overrides
    )
    assert "class EcoMAX860P(CustomParameters):" in module_content
    assert "ParameterOverride(" in module_content
    assert "descriptions = {" in module_content
    assert "power_switch" in module_content

    test_content = generate_test_module(
        product_info,
        descriptions,
        [
            (0, ParameterValues(value=1, min_value=0, max_value=1)),
            (1, ParameterValues(value=50, min_value=20, max_value=80)),
            (2, ParameterValues(value=50, min_value=20, max_value=80)),
        ],
    )
    assert "STATE_ON" in test_content
    assert "STATE_OFF" in test_content
    assert '("power_switch", STATE_ON, STATE_OFF, STATE_ON, None)' in test_content
    assert (
        "a_very_long_parameter_name_that_forces_multi_line_wrapping_in_test_row"
        in test_content
    )
    compile(module_content, "<ecomax_860p>", "exec")
    compile(test_content, "<test_ecomax_860p>", "exec")


def test_codegen_empty_descriptions() -> None:
    """Test generating module with empty descriptions outputs empty dict."""
    product_info = ProductInfo(
        type=ProductType.ECOMAX_P,
        id=1,
        uid="*TEST*",
        logo=0,
        image=0,
        model="ecoMAX 100",
    )
    module_content = generate_custom_parameter_module(
        product_info, descriptions={}, overrides=()
    )
    assert "descriptions = {}" in module_content
    compile(module_content, "<empty>", "exec")


def test_codegen_empty_test_rows_raises_value_error() -> None:
    """Test generating test module with no matching rows raises ValueError."""
    product_info = ProductInfo(
        type=ProductType.ECOMAX_P,
        id=1,
        uid="*TEST*",
        logo=0,
        image=0,
        model="ecoMAX 100",
    )
    with pytest.raises(ValueError, match="No mapped parameters to generate tests for."):
        generate_test_module(product_info, descriptions={}, frame_parameters=[])


def test_codegen_unsupported_description_module_raises() -> None:
    """Test description from unsupported module raises ValueError."""
    product_info = ProductInfo(
        type=ProductType.ECOMAX_P,
        id=1,
        uid="*TEST*",
        logo=0,
        image=0,
        model="ecoMAX 100",
    )

    @dataclass(slots=True)
    class CustomExternalDescription(ParameterDescription):
        """Unsupported custom description."""

    CustomExternalDescription.__module__ = "unknown.custom.module"

    with pytest.raises(ValueError, match="Unsupported parameter description class"):
        generate_custom_parameter_module(
            product_info,
            descriptions={0: CustomExternalDescription(name="unsupported")},
        )


def test_format_field_value() -> None:
    """Test _format_field_value with float integers and strings."""
    assert _format_field_value("step", 2.0) == "2"
    assert _format_field_value("custom_str", "hello") == '"hello"'
