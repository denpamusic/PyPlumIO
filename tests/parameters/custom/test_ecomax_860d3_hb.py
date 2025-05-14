"""Contains test for ecoMAX 860D3-HB custom parameters."""

from __future__ import annotations

from math import isclose

import pytest

from pyplumio.const import STATE_OFF, STATE_ON, ProductType, State, UnitOfMeasurement
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.frames.responses import EcomaxParametersResponse
from pyplumio.parameters import NumericType
from pyplumio.parameters.ecomax import EcomaxNumber, EcomaxParameter, EcomaxSwitch
from pyplumio.structures.ecomax_parameters import ATTR_ECOMAX_PARAMETERS
from pyplumio.structures.product_info import ATTR_PRODUCT, ProductInfo
from tests.conftest import DEFAULT_TOLERANCE, class_from_json

CELSIUS = UnitOfMeasurement.CELSIUS


def _compare_parameter_values(
    a: NumericType | State | None, b: NumericType | State | None
) -> bool:
    """Compare the values."""
    if isinstance(a, float) and isinstance(b, float):
        return isclose(a, b, rel_tol=DEFAULT_TOLERANCE)
    else:
        return True if a == b else False


@pytest.mark.parametrize(
    ("name", "cls", "value", "min_value", "max_value", "unit_of_measurement"),
    [
        ("__unknown_parameter_1", EcomaxNumber, None, None, None, None),
        ("summer_mode", EcomaxNumber, 1, 0, 2, None),
        ("summer_mode_enable_temp", EcomaxNumber, 16, 5, 30, CELSIUS),
        ("summer_mode_disable_temp", EcomaxNumber, 10, 1, 15, CELSIUS),
        ("water_heater_target_temp", EcomaxNumber, 38, 30, 60, CELSIUS),
        ("min_water_heater_target_temp", EcomaxNumber, 30, 20, 55, CELSIUS),
        ("max_water_heater_target_temp", EcomaxNumber, 60, 25, 80, CELSIUS),
        ("__unknown_parameter_2", EcomaxNumber, None, None, None, None),
        ("water_heater_work_mode", EcomaxNumber, 2, 0, 2, None),
        ("water_heater_hysteresis", EcomaxNumber, 7, 1, 20, CELSIUS),
        (
            "water_heater_disinfection",
            EcomaxSwitch,
            STATE_OFF,
            STATE_OFF,
            STATE_ON,
            None,
        ),
    ],
)
@class_from_json(
    EcomaxParametersResponse,
    "parameters/ecomax_860d3_hb.json",
    arguments=("message",),
)
async def test_custom_parameters(
    ecomax_860d3_hb: EcomaxParametersResponse,
    ecomax: EcoMAX,
    name: str,
    cls: type[EcomaxParameter],
    value: NumericType | None,
    min_value: NumericType | None,
    max_value: NumericType | None,
    unit_of_measurement: UnitOfMeasurement | None,
) -> None:
    """Test custom parameters for ecoMAX 860D3-HB.

    Thanks @KryspianClash for testdata.
    """
    ecomax.data[ATTR_PRODUCT] = ProductInfo(
        type=ProductType.ECOMAX_P,
        id=48,
        uid="*TEST*",
        logo=48,
        image=1,
        model="ecoMAX 860D3-HB",
    )
    ecomax.handle_frame(ecomax_860d3_hb)
    await ecomax.wait_until_done()
    assert ecomax.data[ATTR_ECOMAX_PARAMETERS] is True

    assert name in ecomax.data
    parameter = ecomax.get_nowait(name, None)
    assert isinstance(parameter, cls)
    if value is None:
        return

    assert _compare_parameter_values(parameter.value, value)
    assert _compare_parameter_values(parameter.min_value, min_value)
    assert _compare_parameter_values(parameter.max_value, max_value)

    if unit_of_measurement is not None:
        assert hasattr(parameter, "unit_of_measurement")
        assert parameter.unit_of_measurement == unit_of_measurement
