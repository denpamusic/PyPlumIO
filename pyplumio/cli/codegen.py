"""Contains code generation utilities for the PyPlumIO CLI."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import fields
import json
from pathlib import Path
from typing import Any, Final

from pyplumio.cli.model import Row
from pyplumio.const import PERCENTAGE, STATE_ON, UnitOfMeasurement
from pyplumio.parameters import ParameterDescription, ParameterValues
from pyplumio.parameters.custom import ParameterOverride, custom_class_name, model_slug
from pyplumio.parameters.ecomax import EcomaxNumberDescription, EcomaxSwitchDescription
from pyplumio.structures.product_info import ProductInfo

CHUNK_SIZE: Final = 40
MAX_LINE_LENGTH: Final = 88
SUPPORTED_DESCRIPTION_MODULES: Final = (
    "pyplumio.parameters.ecomax",
    "pyplumio.parameters.mixer",
    "pyplumio.parameters.thermostat",
)

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
    "    [\n{rows_str}\n    ],\n)\n"
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


def generate_json_data(message: bytes) -> str:
    """Generate test data JSON content."""
    hex_str = message.hex().upper()
    chunks = [hex_str[i : i + CHUNK_SIZE] for i in range(0, len(hex_str), CHUNK_SIZE)]
    data = [{"message": {"items": chunks, "__bytearray__": True}}]
    return f"{json.dumps(data, indent=2)}\n"


def _format_field_value(field_name: str, value: Any) -> str:
    """Format single field value for code generation."""
    if field_name == "unit_of_measurement":
        if value in (PERCENTAGE, "%"):
            return "PERCENTAGE"
        return f"UnitOfMeasurement.{UnitOfMeasurement(value).name}"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, str):
        return f'"{value}"'
    return str(value)


def _format_description(
    description: ParameterDescription,
) -> tuple[str, list[str]]:
    """Format description class name and non-default arguments."""
    arguments = [f'name="{description.name}"']
    for field in fields(description):
        if field.name == "name":
            continue
        value = getattr(description, field.name)
        if value != field.default:
            arguments.append(f"{field.name}={_format_field_value(field.name, value)}")
    return type(description).__name__, arguments


def _format_dict_entry(index: int, description: ParameterDescription) -> str:
    """Format single descriptions dict entry with 88-column wrapping."""
    class_name, arguments = _format_description(description)
    prefix = f"        {index}: "
    single_line = f"{class_name}({', '.join(arguments)})"
    if len(prefix) + len(single_line) + 1 <= MAX_LINE_LENGTH:
        return f"{prefix}{single_line},"
    body = "\n".join(f"            {arg}," for arg in arguments)
    return f"{prefix}{class_name}(\n{body}\n        ),"


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


def _get_description_module(description: ParameterDescription) -> str:
    """Return the module path for a description, validating it is supported."""
    module = type(description).__module__
    if module in SUPPORTED_DESCRIPTION_MODULES:
        return module
    raise ValueError(
        f"Unsupported parameter description class '{type(description).__name__}' "
        f"from module '{module}'"
    )


def _collect_module_imports(
    descriptions: Mapping[int, ParameterDescription],
    overrides: Sequence[ParameterOverride],
) -> list[str]:
    """Collect required module imports."""
    all_descriptions = list(descriptions.values()) + [
        override.replacement for override in overrides
    ]
    units = {
        getattr(description, "unit_of_measurement", None)
        for description in all_descriptions
    }
    has_percentage = any(unit in (PERCENTAGE, "%") for unit in units)
    has_unit_of_measurement = any(unit not in (None, PERCENTAGE, "%") for unit in units)
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

    modules: dict[str, set[str]] = {}
    for description in all_descriptions:
        module_name = _get_description_module(description)
        modules.setdefault(module_name, set()).add(type(description).__name__)

    for module_name in SUPPORTED_DESCRIPTION_MODULES:
        if module_name in modules:
            class_names = sorted(modules[module_name])
            lines.append(f"from {module_name} import {', '.join(class_names)}")
    return lines


def generate_custom_parameter_module(
    product_info: ProductInfo,
    descriptions: Mapping[int, ParameterDescription],
    overrides: Sequence[ParameterOverride] | None = None,
) -> str:
    """Generate the custom parameter module file content."""
    slug = model_slug(product_info.model)
    parameter_overrides = overrides or ()
    override_lines = "\n".join(
        _format_override_entry(override) for override in parameter_overrides
    )
    description_lines = "\n".join(
        _format_dict_entry(index, description)
        for index, description in sorted(descriptions.items())
        if isinstance(description, (EcomaxNumberDescription, EcomaxSwitchDescription))
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
        imports="\n".join(_collect_module_imports(descriptions, parameter_overrides)),
        override_block=(
            f"    overrides = (\n{override_lines}\n    )\n\n"
            if parameter_overrides
            else ""
        ),
        description_block=description_block,
    )


def _build_test_row(
    description: EcomaxNumberDescription | EcomaxSwitchDescription,
    values: ParameterValues,
) -> tuple[str, bool, bool]:
    """Build single parametrize row and flag unit/switch usage."""
    row = Row(0, values, description=description)
    is_switch = isinstance(description, EcomaxSwitchDescription)
    value = (
        ("STATE_ON" if row.value == STATE_ON else "STATE_OFF")
        if is_switch
        else str(row.value)
    )
    min_value, max_value = (
        ("STATE_OFF", "STATE_ON")
        if is_switch
        else (str(row.min_value), str(row.max_value))
    )
    unit = getattr(description, "unit_of_measurement", None)
    is_percentage = unit in (PERCENTAGE, "%")
    unit_string = (
        "None"
        if unit is None
        else (
            "PERCENTAGE"
            if is_percentage
            else f"UnitOfMeasurement.{UnitOfMeasurement(unit).name}"
        )
    )
    single_line = (
        f'        ("{description.name}", {value}, {min_value}, {max_value},'
        f" {unit_string}),"
    )
    if len(single_line) <= MAX_LINE_LENGTH:
        return single_line, is_percentage, is_switch
    return (
        f'        (\n            "{description.name}",\n            {value},\n'
        f"            {min_value},\n            {max_value},\n"
        f"            {unit_string},\n        ),",
        is_percentage,
        is_switch,
    )


def generate_test_module(
    product_info: ProductInfo,
    descriptions: Mapping[int, ParameterDescription],
    frame_parameters: Sequence[tuple[int, ParameterValues]],
) -> str:
    """Generate the custom parameter test module content."""
    slug = model_slug(product_info.model)
    values_map = dict(frame_parameters)
    rows: list[str] = []
    has_percentage = has_switch = False
    for index, description in sorted(descriptions.items()):
        if index in values_map and isinstance(
            description, (EcomaxNumberDescription, EcomaxSwitchDescription)
        ):
            row_string, percentage_flag, switch_flag = _build_test_row(
                description, values_map[index]
            )
            rows.append(row_string)
            has_percentage = has_percentage or percentage_flag
            has_switch = has_switch or switch_flag

    if not rows:
        raise ValueError("No mapped parameters to generate tests for.")

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
        rows_str="\n".join(rows),
    )


def generate_all_files(
    product_info: ProductInfo,
    descriptions: Mapping[int, ParameterDescription],
    overrides: Sequence[ParameterOverride] | None,
    frame_message: bytes,
    frame_parameters: Sequence[tuple[int, ParameterValues]],
    output_dir: Path,
) -> dict[Path, str]:
    """Generate all three parameter mapping files."""
    slug = model_slug(product_info.model)
    return {
        output_dir / f"pyplumio/parameters/custom/{slug}.py": (
            generate_custom_parameter_module(product_info, descriptions, overrides)
        ),
        output_dir / f"tests/parameters/custom/test_{slug}.py": (
            generate_test_module(product_info, descriptions, frame_parameters)
        ),
        output_dir / f"tests/testdata/parameters/{slug}.json": (
            generate_json_data(frame_message)
        ),
    }


def write_files(files: dict[Path, str]) -> None:
    """Write generated files to filesystem."""
    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")


__all__ = (
    "generate_all_files",
    "generate_custom_parameter_module",
    "generate_json_data",
    "generate_test_module",
    "write_files",
)
