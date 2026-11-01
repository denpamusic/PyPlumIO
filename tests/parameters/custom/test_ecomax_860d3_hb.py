"""Contains test for ecoMAX 860D3-HB custom parameters."""

from __future__ import annotations

import pytest

from pyplumio.const import STATE_OFF, STATE_ON, ProductType, State, UnitOfMeasurement
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.frames.responses import EcomaxParametersResponse
from pyplumio.parameters import Numeric
from pyplumio.parameters.ecomax import EcomaxNumber, EcomaxSwitch
from pyplumio.structures.ecomax_parameters import ATTR_ECOMAX_PARAMETERS
from pyplumio.structures.product_info import ATTR_PRODUCT, ProductInfo
from tests.conftest import class_from_json, equal_parameter_value


@pytest.mark.parametrize(
    ("name", "value", "min_value", "max_value", "unit_of_measurement"),
    [
        ("__unknown_parameter_1", 70, 60, 80, None),
        ("summer_mode", 1, 0, 2, None),
        ("summer_mode_enable_temp", 16, 5, 30, UnitOfMeasurement.CELSIUS),
        ("summer_mode_disable_temp", 10, 1, 15, UnitOfMeasurement.CELSIUS),
        ("water_heater_target_temp", 38, 30, 60, UnitOfMeasurement.CELSIUS),
        ("min_water_heater_target_temp", 30, 20, 55, UnitOfMeasurement.CELSIUS),
        ("max_water_heater_target_temp", 60, 25, 80, UnitOfMeasurement.CELSIUS),
        ("water_heater_feeding_extension", 0, 0, 99, None),
        ("water_heater_work_mode", 2, 0, 2, None),
        ("water_heater_hysteresis", 7, 1, 20, UnitOfMeasurement.CELSIUS),
        ("water_heater_disinfection", STATE_OFF, STATE_OFF, STATE_ON, None),
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
    value: Numeric | State,
    min_value: Numeric | State,
    max_value: Numeric | State,
    unit_of_measurement: UnitOfMeasurement | str | None,
) -> None:
    """Test custom parameters for ecoMAX 860D3-HB.

    Thanks @KryspianClash for testdata.
    """
    await ecomax.dispatch(
        ATTR_PRODUCT,
        ProductInfo(
            type=ProductType.ECOMAX_P,
            id=48,
            uid="*TEST*",
            logo=48,
            image=2,
            model="ecoMAX 860D3-HB",
        ),
    )
    ecomax.handle_frame(ecomax_860d3_hb)
    await ecomax.wait_until_done()
    assert ecomax.data[ATTR_ECOMAX_PARAMETERS] is True

    parameter = ecomax.get_nowait(name)
    assert isinstance(
        parameter, EcomaxSwitch if isinstance(value, str) else EcomaxNumber
    )
    assert equal_parameter_value(parameter.value, value)
    assert equal_parameter_value(parameter.min_value, min_value)
    assert equal_parameter_value(parameter.max_value, max_value)
    assert getattr(parameter, "unit_of_measurement", None) == unit_of_measurement
