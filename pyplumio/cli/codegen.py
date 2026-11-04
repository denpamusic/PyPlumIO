"""Contains code generation utilities for the PyPlumIO CLI."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
from pathlib import Path
from typing import Final

from pyplumio.cli.model import Row
from pyplumio.const import PERCENTAGE, STATE_ON, UnitOfMeasurement
from pyplumio.parameters import ParameterDescription, ParameterValues
from pyplumio.parameters.custom import ParameterOverride, custom_class_name, model_slug
from pyplumio.parameters.ecomax import EcomaxNumberDescription, EcomaxSwitchDescription
from pyplumio.structures.product_info import ProductInfo

CHUNK_SIZE: Final = 40
MAX_LINE_LENGTH: Final = 88

MODULE_TEMPLATE: Final = (
    '"""Contains patch for {model}."""\n\nfrom __future__ import annotations\n\n'
    "{imports}\n\n\nclass {class_name}(CustomParameters):\n"
    '    """Custom parameters for {model}."""\n\n'
    '    signature = Signature(model="{model}", id={product_id})\n\n'
    "{override_block}    descriptions = {{\n{description_lines}\n    }}\n"
)

TEST_TEMPLATE: Final = (
    '"""Contains test for {model} custom parameters."""\n\n'
    "from __future__ import annotations\n\nimport pytest\n\n"
    "from pyplumio.const import (\n{const_str}\n)\n"
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


def _format_description(
    description: ParameterDescription,
) -> tuple[str, list[str]]:
    """Format description class name and arguments."""
    args = [f'name="{description.name}"']
    if isinstance(description, EcomaxSwitchDescription):
        return "EcomaxSwitchDescription", args
    if (step := getattr(description, "step", 1)) not in (1, 1.0):
        step_val = int(step) if float(step).is_integer() else step
        args.append(f"step={step_val}")
    if (offset := getattr(description, "offset", 0)) != 0:
        args.append(f"offset={offset}")
    if (unit := getattr(description, "unit_of_measurement", None)) is not None:
        unit_name = (
            "PERCENTAGE"
            if unit in (PERCENTAGE, "%")
            else f"UnitOfMeasurement.{UnitOfMeasurement(unit).name}"
        )
        args.append(f"unit_of_measurement={unit_name}")
    return "EcomaxNumberDescription", args


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
    single_repl = f"{class_name}({', '.join(arguments)})"
    prefix = f'        ParameterOverride(original="{override.original}", replacement='
    if len(prefix) + len(single_repl) + 2 <= MAX_LINE_LENGTH:
        return f"{prefix}{single_repl}),"
    body = "\n".join(f"                {arg}," for arg in arguments)
    repl = (
        f"            replacement={single_repl},"
        if len(f"            replacement={single_repl},") <= MAX_LINE_LENGTH
        else f"            replacement={class_name}(\n{body}\n            ),"
    )
    return (
        f'        ParameterOverride(\n            original="{override.original}",\n'
        f"{repl}\n        ),"
    )


def _collect_module_imports(
    descriptions: Mapping[int, ParameterDescription],
    overrides: Sequence[ParameterOverride],
) -> list[str]:
    """Collect required module imports."""
    all_desc = list(descriptions.values()) + [o.replacement for o in overrides]
    units = {getattr(d, "unit_of_measurement", None) for d in all_desc}
    has_pct = any(u in (PERCENTAGE, "%") for u in units)
    has_uom = any(u not in (None, PERCENTAGE, "%") for u in units)
    consts = [
        *(["PERCENTAGE"] if has_pct else []),
        *(["UnitOfMeasurement"] if has_uom else []),
    ]
    lines = [f"from pyplumio.const import {', '.join(consts)}"] if consts else []
    custom = [
        "CustomParameters",
        *(["ParameterOverride"] if overrides else []),
        "Signature",
    ]
    lines.append(f"from pyplumio.parameters.custom import {', '.join(custom)}")
    ecomax = [
        name
        for name, cls in (
            ("EcomaxNumberDescription", EcomaxNumberDescription),
            ("EcomaxSwitchDescription", EcomaxSwitchDescription),
        )
        if any(isinstance(d, cls) for d in all_desc)
    ]
    if ecomax:
        lines.append(f"from pyplumio.parameters.ecomax import {', '.join(ecomax)}")
    return lines


def generate_custom_parameter_module(
    product_info: ProductInfo,
    descriptions: Mapping[int, ParameterDescription],
    overrides: Sequence[ParameterOverride] | None = None,
) -> str:
    """Generate the custom parameter module file content."""
    slug, ovs = model_slug(product_info.model), overrides or ()
    ov_lines = "\n".join(_format_override_entry(o) for o in ovs)
    desc_lines = "\n".join(
        _format_dict_entry(index, desc)
        for index, desc in sorted(descriptions.items())
        if isinstance(desc, (EcomaxNumberDescription, EcomaxSwitchDescription))
    )
    return MODULE_TEMPLATE.format(
        model=product_info.model,
        product_id=product_info.id,
        class_name=custom_class_name(slug),
        imports="\n".join(_collect_module_imports(descriptions, ovs)),
        override_block=f"    overrides = (\n{ov_lines}\n    )\n\n" if ovs else "",
        description_lines=desc_lines,
    )


def _build_test_row(
    description: EcomaxNumberDescription | EcomaxSwitchDescription,
    values: ParameterValues,
) -> tuple[str, bool, bool]:
    """Build single parametrize row and flag unit/switch usage."""
    row = Row(0, values, description=description)
    is_sw = isinstance(description, EcomaxSwitchDescription)
    val = (
        ("STATE_ON" if row.value == STATE_ON else "STATE_OFF")
        if is_sw
        else str(row.value)
    )
    mn, mx = (
        ("STATE_OFF", "STATE_ON") if is_sw else (str(row.min_value), str(row.max_value))
    )
    unit = getattr(description, "unit_of_measurement", None)
    is_pct = unit in (PERCENTAGE, "%")
    u_str = (
        "None"
        if unit is None
        else (
            "PERCENTAGE"
            if is_pct
            else f"UnitOfMeasurement.{UnitOfMeasurement(unit).name}"
        )
    )
    single = f'        ("{description.name}", {val}, {mn}, {mx}, {u_str}),'
    if len(single) <= MAX_LINE_LENGTH:
        return single, is_pct, is_sw
    return (
        f'        (\n            "{description.name}",\n            {val},\n'
        f"            {mn},\n            {mx},\n            {u_str},\n        ),",
        is_pct,
        is_sw,
    )


def generate_test_module(
    product_info: ProductInfo,
    descriptions: Mapping[int, ParameterDescription],
    frame_parameters: Sequence[tuple[int, ParameterValues]],
) -> str:
    """Generate the custom parameter test module content."""
    slug, values_map = model_slug(product_info.model), dict(frame_parameters)
    rows: list[str] = []
    has_percentage = has_switch = False
    for index, desc in sorted(descriptions.items()):
        if index in values_map and isinstance(
            desc, (EcomaxNumberDescription, EcomaxSwitchDescription)
        ):
            row_str, p_flag, sw_flag = _build_test_row(desc, values_map[index])
            rows.append(row_str)
            has_percentage = has_percentage or p_flag
            has_switch = has_switch or sw_flag

    consts = (
        (["PERCENTAGE"] if has_percentage else [])
        + (["STATE_OFF", "STATE_ON"] if has_switch else [])
        + ["ProductType", "State", "UnitOfMeasurement"]
    )
    return TEST_TEMPLATE.format(
        model=product_info.model,
        type_name=product_info.type.name,
        product_id=product_info.id,
        slug=slug,
        parameter_count=len(frame_parameters),
        const_str="\n".join(f"    {item}," for item in consts),
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
