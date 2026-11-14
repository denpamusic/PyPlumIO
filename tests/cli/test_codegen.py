"""Contains tests for the CLI codegen module."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest

from pyplumio.cli.codegen import (
    _format_field_value,
    extract_comments,
    generate_all_files,
    generate_custom_parameter_module,
    generate_test_module,
    write_files,
    write_zip,
)
from pyplumio.const import PERCENTAGE, ProductType, UnitOfMeasurement
from pyplumio.frames.responses import EcomaxServiceParametersResponse
from pyplumio.parameters import ParameterValues
from pyplumio.parameters.custom import ParameterOverride
from pyplumio.parameters.custom.ecomax_350p2_zf import EcoMAX350P2ZF
from pyplumio.parameters.ecomax import EcomaxNumberDescription, EcomaxSwitchDescription
from pyplumio.structures.ecomax_service_parameters import ATTR_ECOMAX_SERVICE_PARAMETERS
from pyplumio.structures.product_info import ProductInfo


def _assert_ruff_clean(tmp_path: Path, slug: str) -> None:
    """Run ruff check and format check on generated files."""
    pytest.importorskip("ruff")
    root_dir = Path(__file__).parent.parent.parent
    pyproject_path = str(root_dir / "pyproject.toml")
    tests_ruff_path = str(root_dir / "tests" / "ruff.toml")

    module_path = tmp_path / "pyplumio" / "parameters" / "custom" / f"{slug}.py"
    module_check = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "--config",
            pyproject_path,
            str(module_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert module_check.returncode == 0, module_check.stdout + module_check.stderr

    test_path = tmp_path / "tests" / "parameters" / "custom" / f"test_{slug}.py"
    test_check = subprocess.run(
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
    assert test_check.returncode == 0, test_check.stdout + test_check.stderr

    format_check = subprocess.run(
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
    assert format_check.returncode == 0, format_check.stdout + format_check.stderr


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

    real_module_path = (
        Path(__file__).parent.parent.parent
        / "pyplumio"
        / "parameters"
        / "custom"
        / "ecomax_350p2_zf.py"
    )
    comments = extract_comments(real_module_path.read_text(encoding="utf-8"))
    assert comments == {113: "0 - pellets, 1 - wood"}

    files = generate_all_files(
        product_info=product_info,
        descriptions=EcoMAX350P2ZF.descriptions,
        overrides=getattr(EcoMAX350P2ZF, "overrides", ()),
        frame_message=raw_bytes,
        frame_parameters=frame_parameters,
        output_dir=tmp_path,
        comments=comments,
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
    assert "        # 0 - pellets, 1 - wood\n        113: " in module_content
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

    _assert_ruff_clean(tmp_path, "ecomax_350p2_zf")


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
            original="max_temp",
            replacement=EcomaxNumberDescription(name="max_temp", step=1, offset=5),
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
        "from pyplumio.parameters.ecomax import "
        "EcomaxNumberDescription, EcomaxSwitchDescription"
    ) in module_content

    # Exec module and verify exact dataclass equality
    code_obj = compile(module_content, "<ecomax_860p>", "exec")
    local_ns: dict[str, object] = {}
    exec(code_obj, local_ns)  # noqa: S102
    generated_class = local_ns["EcoMAX860P"]
    assert getattr(generated_class, "descriptions") == descriptions
    assert getattr(generated_class, "overrides") == tuple(overrides)

    write_files(files)
    _assert_ruff_clean(tmp_path, "ecomax_860p")


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


def test_format_field_value() -> None:
    """Test _format_field_value with float integers and strings."""
    assert _format_field_value("step", 2.0) == "2"
    assert _format_field_value("custom_str", "hello") == '"hello"'


def test_write_zip(tmp_path: Path) -> None:
    """Test writing generated parameter files into a ZIP archive."""
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
    real_module_path = (
        Path(__file__).parent.parent.parent
        / "pyplumio"
        / "parameters"
        / "custom"
        / "ecomax_350p2_zf.py"
    )
    comments = extract_comments(real_module_path.read_text(encoding="utf-8"))
    assert comments == {113: "0 - pellets, 1 - wood"}

    files = generate_all_files(
        product_info=product_info,
        descriptions=EcoMAX350P2ZF.descriptions,
        overrides=getattr(EcoMAX350P2ZF, "overrides", ()),
        frame_message=raw_bytes,
        frame_parameters=frame_parameters,
        output_dir=tmp_path,
        comments=comments,
    )

    zip_path = tmp_path / "archives" / "ecomax_350p2_zf.zip"
    write_zip(zip_path, files, tmp_path)
    assert zip_path.is_file()

    expected_members = {
        "pyplumio/parameters/custom/ecomax_350p2_zf.py",
        "tests/parameters/custom/test_ecomax_350p2_zf.py",
        "tests/testdata/parameters/ecomax_350p2_zf.json",
    }
    with zipfile.ZipFile(zip_path, "r") as archive:
        assert set(archive.namelist()) == expected_members
        for path, expected_content in files.items():
            member = path.relative_to(tmp_path).as_posix()
            assert archive.read(member).decode("utf-8") == expected_content


def test_codegen_with_comments(tmp_path: Path) -> None:
    """Test generating custom parameter module and files with wrapped comments."""
    product_info = ProductInfo(
        type=ProductType.ECOMAX_P,
        id=90,
        uid="*TEST*",
        logo=0,
        image=0,
        model="ecoMAX 350P2-ZF",
    )
    descriptions: dict[int, EcomaxNumberDescription | EcomaxSwitchDescription] = {
        0: EcomaxSwitchDescription(name="mode_switch"),
        1: EcomaxSwitchDescription(name="aux_switch"),
        2: EcomaxNumberDescription(
            name="boiler_temp",
            step=1,
            offset=0,
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
    }
    long_comment = (
        "Long comment that wraps across multiple lines because it exceeds the "
        "seventy-eight character limit per comment line."
    )
    comments = {
        0: "0 - off, 1 - on",
        1: "# 0 - off, 1 - on",
        2: long_comment,
    }

    module_content = generate_custom_parameter_module(
        product_info, descriptions, comments=comments
    )
    assert "        # 0 - off, 1 - on\n        0: EcomaxSwitchDescription" in (
        module_content
    )
    assert "        # 0 - off, 1 - on\n        1: EcomaxSwitchDescription" in (
        module_content
    )
    assert "# #" not in module_content

    comment_lines = [
        line for line in module_content.splitlines() if line.startswith("        # ")
    ]
    assert len(comment_lines) >= 4
    assert all(len(line) <= 88 for line in comment_lines)
    assert extract_comments(module_content) == {
        0: "0 - off, 1 - on",
        1: "0 - off, 1 - on",
        2: long_comment,
    }

    custom_dir = (
        Path(__file__).parent.parent.parent / "pyplumio" / "parameters" / "custom"
    )
    assert (
        extract_comments(
            (custom_dir / "ecomax_860d3_hb.py").read_text(encoding="utf-8")
        )
        == {}
    )
    assert extract_comments(
        (custom_dir / "ecomax_860p4_nm_touch.py").read_text(encoding="utf-8")
    ) == {
        23: (
            "0 - standard, 1 - fuzzy logic. Kept as a number, because the "
            "controller allows a third value (2) with unknown meaning."
        ),
        90: "0 - off, 1 - priority, 2 - no priority.",
        210: "0 - off, 1 - 4D valve, 2 - 3D valve (by panel list order).",
        215: "0 - reserve boiler, 1 - alarms, 2 - circulation pump.",
    }
    assert extract_comments(
        "# top-level comment\n"
        "    # 4-space comment\n"
        "        # separated by blank line\n"
        "\n"
        '        1: EcomaxSwitchDescription(name="a"),\n'
        '        2: EcomaxSwitchDescription(name="b"),  # inline comment\n'
        "        # comment before unindented entry\n"
        "10: something\n"
        "        # comment before 4-space entry\n"
        "    11: something\n"
        "        # first line\n"
        "        #\n"
        "        # second line\n"
        '        12: EcomaxSwitchDescription(name="c"),\n'
        "        #unspaced malformed comment\n"
        '        13: EcomaxSwitchDescription(name="d"),\n'
        "        # comment before bare integer without colon\n"
        "        14\n"
        "        # comment before unicode digit entry\n"
        "        ²: something\n"
    ) == {12: "first line second line"}

    files = generate_all_files(
        product_info=product_info,
        descriptions=descriptions,
        overrides=(),
        frame_message=b"\x00" * 40,
        frame_parameters=[
            (0, ParameterValues(value=1, min_value=0, max_value=1)),
            (1, ParameterValues(value=0, min_value=0, max_value=1)),
            (2, ParameterValues(value=50, min_value=10, max_value=80)),
        ],
        output_dir=tmp_path,
        comments=comments,
    )
    generated_module = files[
        tmp_path / "pyplumio" / "parameters" / "custom" / "ecomax_350p2_zf.py"
    ]
    assert generated_module == module_content
    compile(generated_module, "<ecomax_350p2_zf>", "exec")

    write_files(files)
    _assert_ruff_clean(tmp_path, "ecomax_350p2_zf")
