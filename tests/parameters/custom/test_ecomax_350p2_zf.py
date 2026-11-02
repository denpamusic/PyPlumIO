"""Contains test for ecoMAX 350P2-ZF custom parameters."""

from __future__ import annotations

import pytest

from pyplumio.const import (
    PERCENTAGE,
    STATE_OFF,
    STATE_ON,
    ProductType,
    State,
    UnitOfMeasurement,
)
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.frames.responses import EcomaxServiceParametersResponse
from pyplumio.parameters import Numeric
from pyplumio.parameters.ecomax import EcomaxServiceNumber, EcomaxServiceSwitch
from pyplumio.structures.ecomax_service_parameters import ATTR_ECOMAX_SERVICE_PARAMETERS
from pyplumio.structures.product_info import ATTR_PRODUCT, ProductInfo
from tests.conftest import class_from_json, equal_parameter_value


@pytest.mark.parametrize(
    ("name", "value", "min_value", "max_value", "unit_of_measurement"),
    [
        ("heating_cycle_time", 5, 1, 30, UnitOfMeasurement.SECONDS),
        ("fuzzy_logic_parameter_a", 5, 2, 8, None),
        ("fuzzy_logic_parameter_b", 50, 20, 120, None),
        ("fuzzy_logic_parameter_c", 50, 0, 75, None),
        ("ignition_fan_power", 30, 30, 50, PERCENTAGE),
        ("ignition_fuel_detection_time", 10, 10, 240, UnitOfMeasurement.SECONDS),
        ("ignition_fuel_dose", 610, 100, 1000, UnitOfMeasurement.GRAMS),
        ("ignition_flue_gas_temp", 45, 40, 150, UnitOfMeasurement.CELSIUS),
        ("ignition_low_power_time", 2, 1, 15, UnitOfMeasurement.MINUTES),
        ("stabilization_fan_power", 40, 30, 60, PERCENTAGE),
        ("stabilization_min_flue_gas_temp", 70, 50, 150, UnitOfMeasurement.CELSIUS),
        ("stabilization_fan_work_time", 3, 1, 10, UnitOfMeasurement.MINUTES),
        ("stabilization_temp_delta", 10, 0, 50, UnitOfMeasurement.CELSIUS),
        ("min_fan_power", 31, 30, 50, PERCENTAGE),
        ("feeder_coefficient", 0.8, 0.1, 2.0, None),
        ("hopper_capacity", 100, 2, 500, UnitOfMeasurement.KILOGRAMS),
        (
            "lower_heating_temp_from_thermostat",
            5,
            0,
            30,
            UnitOfMeasurement.CELSIUS,
        ),
        ("boiler_alert_temp", 90, 85, 95, UnitOfMeasurement.CELSIUS),
        ("thermostat_mode_switch", STATE_ON, STATE_OFF, STATE_ON, None),
        (
            "feeder2_work_time_extension",
            4,
            0,
            250,
            UnitOfMeasurement.SECONDS,
        ),
        ("fuel_type", 0, 0, 1, None),
    ],
)
@class_from_json(
    EcomaxServiceParametersResponse,
    "parameters/ecomax_350p2_zf.json",
    arguments=("message",),
)
async def test_custom_parameters(
    ecomax_350p2_zf: EcomaxServiceParametersResponse,
    ecomax: EcoMAX,
    name: str,
    value: Numeric | State,
    min_value: Numeric | State,
    max_value: Numeric | State,
    unit_of_measurement: UnitOfMeasurement | str | None,
) -> None:
    """Test custom parameters for ecoMAX 350P2-ZF."""
    await ecomax.dispatch(
        ATTR_PRODUCT,
        ProductInfo(
            type=ProductType.ECOMAX_P,
            id=90,
            uid="*TEST*",
            logo=0,
            image=0,
            model="ecoMAX 350P2-ZF",
        ),
    )
    ecomax.handle_frame(ecomax_350p2_zf)
    await ecomax.wait_until_done()
    assert len(ecomax.data[ATTR_ECOMAX_SERVICE_PARAMETERS]) == 128

    parameter = ecomax.get_nowait(name)
    assert isinstance(
        parameter,
        EcomaxServiceSwitch if isinstance(value, str) else EcomaxServiceNumber,
    )
    assert equal_parameter_value(parameter.value, value)
    assert equal_parameter_value(parameter.min_value, min_value)
    assert equal_parameter_value(parameter.max_value, max_value)
    assert getattr(parameter, "unit_of_measurement", None) == unit_of_measurement
