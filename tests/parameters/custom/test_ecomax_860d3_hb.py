"""Contains test for ecoMAX 860D3-HB custom parameters."""

from __future__ import annotations

from typing import Final

import pytest

from pyplumio.const import STATE_OFF, STATE_ON, ProductType, UnitOfMeasurement
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.frames.responses import EcomaxParametersResponse
from pyplumio.parameters import Numeric
from pyplumio.parameters.ecomax import EcomaxNumber, EcomaxParameter, EcomaxSwitch
from pyplumio.structures.ecomax_parameters import ATTR_ECOMAX_PARAMETERS
from pyplumio.structures.product_info import ATTR_PRODUCT, ProductInfo
from tests.conftest import class_from_json, equal_parameter_value

CELSIUS: Final = UnitOfMeasurement.CELSIUS


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
        ("water_heater_feeding_extension", EcomaxNumber, 0, 0, 99, None),
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
    value: Numeric | None,
    min_value: Numeric | None,
    max_value: Numeric | None,
    unit_of_measurement: UnitOfMeasurement | None,
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

    assert name in ecomax.data
    parameter = ecomax.get_nowait(name, None)
    assert isinstance(parameter, cls)
    if value is None:
        return

    assert equal_parameter_value(parameter.value, value)
    assert equal_parameter_value(parameter.min_value, min_value)
    assert equal_parameter_value(parameter.max_value, max_value)

    if unit_of_measurement is not None:
        assert hasattr(parameter, "unit_of_measurement")
        assert parameter.unit_of_measurement == unit_of_measurement
