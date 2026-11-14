"""Contains code generation utilities for the PyPlumIO CLI."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import fields
import json
from pathlib import Path
import textwrap
from typing import Any, Final, Literal, cast
import zipfile

from pyplumio.cli.model import Row
from pyplumio.const import PERCENTAGE, STATE_ON, UnitOfMeasurement
from pyplumio.parameters import ParameterValues
from pyplumio.parameters.custom import ParameterOverride, custom_class_name, model_slug
from pyplumio.parameters.ecomax import (
    EcomaxNumberDescription,
    EcomaxParameterDescription,
    EcomaxSwitchDescription,
)
from pyplumio.structures.product_info import ProductInfo

CHUNK_SIZE: Final = 77
MAX_LINE_LENGTH: Final = 88
COMMENT_PREFIX: Final = "        # "
ENTRY_PREFIX: Final = "        "

MODULE_TEMPLATE: Final = (
    '"""Contains patch for {model}."""\n\nfrom __future__ import annotations\n\n'
    "{imports}\n\n\nclass {class_name}(CustomParameters):\n"
    '    """Custom parameters for {model}."""\n\n'
    '    signature = Signature(model="{model}", id={product_id})\n\n'
    "{override_block}{description_block}"
)

TEST_TEMPLATE: Final = (
    '"""Contains test for {model} custom parameters."""\n\n'
    "from __future__ import annotations\n\nimport pytest\n\n"
    "{const_import}\n"
    "from pyplumio.devices.ecomax import EcoMAX\n"
    "from pyplumio.frames.responses import EcomaxServiceParametersResponse\n"
    "from pyplumio.parameters import Numeric\n"
    "from pyplumio.parameters.ecomax import EcomaxServiceNumber, EcomaxServiceSwitch\n"
    "from pyplumio.structures.ecomax_service_parameters import "
    "ATTR_ECOMAX_SERVICE_PARAMETERS\n"
    "from pyplumio.structures.product_info import ATTR_PRODUCT, ProductInfo\n"
    "from tests.conftest import class_from_json, equal_parameter_value\n\n\n"
    "@pytest.mark.parametrize(\n"
    '    ("name", "value", "min_value", "max_value", "unit_of_measurement"),\n'
    "    [\n{row_lines}\n    ],\n)\n"
    "@class_from_json(\n    EcomaxServiceParametersResponse,\n"
    '    "parameters/{slug}.json",\n    arguments=("message",),\n)\n'
    "async def test_custom_parameters(\n    {slug}: EcomaxServiceParametersResponse,\n"
    "    ecomax: EcoMAX,\n    name: str,\n    value: Numeric | State,\n"
    "    min_value: Numeric | State,\n    max_value: Numeric | State,\n"
    "    unit_of_measurement: UnitOfMeasurement | str | None,\n) -> None:\n"
    '    """Test custom parameters for {model}."""\n'
    "    await ecomax.dispatch(\n        ATTR_PRODUCT,\n"
    "        ProductInfo(\n            type=ProductType.{type_name},\n"
    '            id={product_id},\n            uid="*TEST*",\n'
    '            logo=0,\n            image=0,\n            model="{model}",\n'
    "        ),\n    )\n    ecomax.handle_frame({slug})\n"
    "    await ecomax.wait_until_done()\n"
    "    assert len(ecomax.data[ATTR_ECOMAX_SERVICE_PARAMETERS]) == "
    "{parameter_count}\n\n"
    "    parameter = ecomax.get_nowait(name)\n"
    "    assert isinstance(\n        parameter,\n"
    "        EcomaxServiceSwitch if isinstance(value, str) else EcomaxServiceNumber,\n"
    "    )\n"
    "    assert equal_parameter_value(parameter.value, value)\n"
    "    assert equal_parameter_value(parameter.min_value, min_value)\n"
    "    assert equal_parameter_value(parameter.max_value, max_value)\n"
    '    assert getattr(parameter, "unit_of_measurement", None) == '
    "unit_of_measurement\n"
)


def _format_unit(unit: UnitOfMeasurement | Literal["%"] | None) -> str:
    """Format unit."""
    if unit is None:
        return "None"

    if unit == PERCENTAGE:
        return "PERCENTAGE"

    return f"UnitOfMeasurement.{UnitOfMeasurement(unit).name}"


def _format_field_value(field_name: str, value: Any) -> str:
    """Format single field value for code generation."""
    if field_name == "unit_of_measurement":
        return _format_unit(value)

    if isinstance(value, float) and value.is_integer():
        return str(int(value))

    if isinstance(value, str):
        return f'"{value}"'

    return str(value)


def _format_description(
    description: EcomaxParameterDescription,
) -> tuple[str, list[str]]:
    """Format description class name and non-default arguments."""
    arguments = [
        f"{field.name}={_format_field_value(field.name, value)}"
        for field in fields(description)
        if (value := getattr(description, field.name)) != field.default
    ]
    return type(description).__name__, arguments


def _format_comment(comment: str) -> str:
    """Format parameter comment with 88-column wrapping."""
    lines = textwrap.wrap(
        comment.lstrip("#").strip(),
        width=MAX_LINE_LENGTH - len(COMMENT_PREFIX),
        break_long_words=False,
        break_on_hyphens=False,
    )
    return "".join(f"{COMMENT_PREFIX}{line}\n" for line in lines)


def _format_dict_entry(
    index: int,
    description: EcomaxParameterDescription,
    comment: str | None = None,
) -> str:
    """Format single descriptions dict entry with 88-column wrapping."""
    comment_prefix = _format_comment(comment) if comment else ""
    class_name, arguments = _format_description(description)
    prefix = f"{ENTRY_PREFIX}{index}: "
    single_line = f"{class_name}({', '.join(arguments)})"
    if len(prefix) + len(single_line) + 1 <= MAX_LINE_LENGTH:
        return f"{comment_prefix}{prefix}{single_line},"

    body = "\n".join(f"            {arg}," for arg in arguments)
    return f"{comment_prefix}{prefix}{class_name}(\n{body}\n        ),"


def _format_override_entry(override: ParameterOverride) -> str:
    """Format single override entry with 88-column wrapping."""
    class_name, arguments = _format_description(override.replacement)
    single_replacement = f"{class_name}({', '.join(arguments)})"
    prefix = f'        ParameterOverride(original="{override.original}", replacement='
    if len(prefix) + len(single_replacement) + 2 <= MAX_LINE_LENGTH:
        return f"{prefix}{single_replacement}),"

    body = "\n".join(f"                {arg}," for arg in arguments)
    replacement = (
        f"            replacement={single_replacement},"
        if len(f"            replacement={single_replacement},") <= MAX_LINE_LENGTH
        else f"            replacement={class_name}(\n{body}\n            ),"
    )
    return (
        f'        ParameterOverride(\n            original="{override.original}",\n'
        f"{replacement}\n        ),"
    )


def _collect_module_imports(
    descriptions: Mapping[int, EcomaxParameterDescription],
    overrides: Sequence[ParameterOverride],
) -> list[str]:
    """Collect required module imports."""
    all_descriptions = list(descriptions.values()) + [
        override.replacement for override in overrides
    ]
    units = {
        description.unit_of_measurement
        for description in all_descriptions
        if isinstance(description, EcomaxNumberDescription)
    }
    has_percentage = PERCENTAGE in units
    has_unit_of_measurement = bool(units - {None, PERCENTAGE})
    consts = [
        *(["PERCENTAGE"] if has_percentage else []),
        *(["UnitOfMeasurement"] if has_unit_of_measurement else []),
    ]
    lines = [f"from pyplumio.const import {', '.join(consts)}"] if consts else []
    custom_imports = [
        "CustomParameters",
        *(["ParameterOverride"] if overrides else []),
        "Signature",
    ]
    lines.append(f"from pyplumio.parameters.custom import {', '.join(custom_imports)}")

    if classes := sorted(
        {type(description).__name__ for description in all_descriptions}
    ):
        lines.append(f"from pyplumio.parameters.ecomax import {', '.join(classes)}")

    return lines


def _format_test_row(
    description: EcomaxParameterDescription,
    values: ParameterValues,
) -> str:
    """Format single parametrize row."""
    row = Row(0, values, description=description)
    if isinstance(description, EcomaxSwitchDescription):
        value = "STATE_ON" if row.value == STATE_ON else "STATE_OFF"
        min_value, max_value = "STATE_OFF", "STATE_ON"
        unit_string = "None"
    else:
        number = cast(EcomaxNumberDescription, description)
        value = str(row.value)
        min_value, max_value = str(row.min_value), str(row.max_value)
        unit_string = _format_unit(number.unit_of_measurement)

    single_line = (
        f'        ("{description.name}", {value}, {min_value}, {max_value},'
        f" {unit_string}),"
    )
    if len(single_line) <= MAX_LINE_LENGTH:
        return single_line

    return (
        f'        (\n            "{description.name}",\n            {value},\n'
        f"            {min_value},\n            {max_value},\n"
        f"            {unit_string},\n        ),"
    )


def _generate_json_data(message: bytes) -> str:
    """Generate test data JSON content."""
    hex_string = message.hex().upper()
    chunks = [
        hex_string[i : i + CHUNK_SIZE] for i in range(0, len(hex_string), CHUNK_SIZE)
    ]
    data = [{"message": {"items": chunks, "__bytearray__": True}}]
    return f"{json.dumps(data, indent=2)}\n"


def _parse_entry_index(line: str) -> int | None:
    """Parse indented dictionary entry index from a source line."""
    if not line.startswith(ENTRY_PREFIX):
        return None

    key, sep, _ = line.removeprefix(ENTRY_PREFIX).partition(":")
    return int(key) if sep and key.isascii() and key.isdigit() else None


def custom_module_path(output_dir: Path, slug: str) -> Path:
    """Return output path for the generated custom parameter module."""
    return output_dir / f"pyplumio/parameters/custom/{slug}.py"


def zip_archive_path(output_dir: Path, slug: str) -> Path:
    """Return output path for the generated ZIP archive."""
    return output_dir / f"{slug}.zip"


def extract_comments(source: str) -> dict[int, str]:
    """Extract parameter comments from custom parameter module source."""
    comments: dict[int, str] = {}
    pending: list[str] = []
    for line in source.splitlines():
        if line.startswith(COMMENT_PREFIX):
            if text := line.removeprefix(COMMENT_PREFIX).strip():
                pending.append(text)

            continue

        if line == COMMENT_PREFIX.rstrip():
            continue

        if pending and (index := _parse_entry_index(line)) is not None:
            comments[index] = " ".join(pending)

        pending.clear()

    return comments


def generate_custom_parameter_module(
    product_info: ProductInfo,
    descriptions: Mapping[int, EcomaxParameterDescription],
    overrides: Sequence[ParameterOverride] = (),
    comments: Mapping[int, str] | None = None,
) -> str:
    """Generate the custom parameter module file content."""
    slug = model_slug(product_info.model)
    comment_map = comments or {}
    override_lines = "\n".join(
        _format_override_entry(override) for override in overrides
    )
    description_lines = "\n".join(
        _format_dict_entry(index, description, comment_map.get(index))
        for index, description in sorted(descriptions.items())
    )
    description_block = (
        f"    descriptions = {{\n{description_lines}\n    }}\n"
        if description_lines
        else "    descriptions = {}\n"
    )
    return MODULE_TEMPLATE.format(
        model=product_info.model,
        product_id=product_info.id,
        class_name=custom_class_name(slug),
        imports="\n".join(_collect_module_imports(descriptions, overrides)),
        override_block=(
            f"    overrides = (\n{override_lines}\n    )\n\n" if overrides else ""
        ),
        description_block=description_block,
    )


def generate_test_module(
    product_info: ProductInfo,
    descriptions: Mapping[int, EcomaxParameterDescription],
    frame_parameters: Sequence[tuple[int, ParameterValues]],
) -> str:
    """Generate the custom parameter test module content."""
    slug = model_slug(product_info.model)
    values_map = dict(frame_parameters)
    mapped = [
        (description, values_map[index])
        for index, description in sorted(descriptions.items())
        if index in values_map
    ]
    if not mapped:
        raise ValueError("No mapped parameters to generate tests for.")

    rows = [_format_test_row(description, values) for description, values in mapped]
    has_percentage = any(
        isinstance(description, EcomaxNumberDescription)
        and description.unit_of_measurement == PERCENTAGE
        for description, _ in mapped
    )
    has_switch = any(
        isinstance(description, EcomaxSwitchDescription) for description, _ in mapped
    )

    consts = (
        (["PERCENTAGE"] if has_percentage else [])
        + (["STATE_OFF", "STATE_ON"] if has_switch else [])
        + ["ProductType", "State", "UnitOfMeasurement"]
    )
    single_const = f"from pyplumio.const import {', '.join(consts)}"
    const_import = (
        single_const
        if len(single_const) <= MAX_LINE_LENGTH
        else "from pyplumio.const import (\n"
        + "\n".join(f"    {item}," for item in consts)
        + "\n)"
    )
    return TEST_TEMPLATE.format(
        model=product_info.model,
        type_name=product_info.type.name,
        product_id=product_info.id,
        slug=slug,
        parameter_count=len(frame_parameters),
        const_import=const_import,
        row_lines="\n".join(rows),
    )


def generate_all_files(
    product_info: ProductInfo,
    descriptions: Mapping[int, EcomaxParameterDescription],
    overrides: Sequence[ParameterOverride],
    frame_message: bytes,
    frame_parameters: Sequence[tuple[int, ParameterValues]],
    output_dir: Path,
    comments: Mapping[int, str] | None = None,
) -> dict[Path, str]:
    """Generate all three parameter mapping files."""
    slug = model_slug(product_info.model)
    return {
        custom_module_path(output_dir, slug): (
            generate_custom_parameter_module(
                product_info, descriptions, overrides, comments=comments
            )
        ),
        output_dir / f"tests/parameters/custom/test_{slug}.py": (
            generate_test_module(product_info, descriptions, frame_parameters)
        ),
        output_dir / f"tests/testdata/parameters/{slug}.json": (
            _generate_json_data(frame_message)
        ),
    }


def write_files(files: Mapping[Path, str]) -> None:
    """Write generated files to filesystem."""
    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")


def write_zip(zip_path: Path, files: Mapping[Path, str], output_dir: Path) -> None:
    """Write generated files to a ZIP archive with repository-relative paths."""
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path, content in files.items():
            archive.writestr(path.relative_to(output_dir).as_posix(), content)


__all__ = (
    "custom_module_path",
    "extract_comments",
    "generate_all_files",
    "generate_custom_parameter_module",
    "generate_test_module",
    "write_files",
    "write_zip",
    "zip_archive_path",
)
