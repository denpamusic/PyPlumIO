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
        ("boiler_power_100", 16, 11, 16, UnitOfMeasurement.KILO_WATT),
        ("boiler_power_50", 10, 4, 15, UnitOfMeasurement.KILO_WATT),
        ("boiler_power_30", 3, 3, 6, UnitOfMeasurement.KILO_WATT),
        ("airflow_power_100", 80, 61, 100, PERCENTAGE),
        ("airflow_power_50", 60, 41, 79, PERCENTAGE),
        ("airflow_power_30", 40, 30, 59, PERCENTAGE),
        ("h2_hysteresis", 3, 1, 30, UnitOfMeasurement.CELSIUS),
        ("h1_hysteresis", 1, 1, 30, UnitOfMeasurement.CELSIUS),
        ("heating_hysteresis", 5, 1, 30, UnitOfMeasurement.CELSIUS),
        ("cycle_duration", 20, 1, 250, UnitOfMeasurement.SECONDS),
        ("min_fuzzy_logic_power", 0, 0, 75, PERCENTAGE),
        ("max_fuzzy_logic_power", 75, 0, 100, PERCENTAGE),
        ("fuzzy_logic_parameter_a", 5, 2, 8, None),
        ("fuzzy_logic_parameter_b", 30, 20, 120, None),
        ("fuzzy_logic_parameter_c", 50, 0, 75, None),
        ("kindling_fan_power", 30, 30, 50, PERCENTAGE),
        ("kindling_fuel_detection_time", 10, 10, 240, UnitOfMeasurement.SECONDS),
        ("kindling_time", 15, 10, 20, UnitOfMeasurement.MINUTES),
        ("kindling_fuel_dose", 610, 100, 1000, UnitOfMeasurement.GRAMS),
        ("kindling_flue_gas_temp", 45, 40, 150, UnitOfMeasurement.CELSIUS),
        ("kindling_low_power_time", 2, 1, 15, UnitOfMeasurement.MINUTES),
        ("stabilization_fan_power", 40, 30, 60, PERCENTAGE),
        ("stabilization_min_flue_gas_temp", 70, 50, 150, UnitOfMeasurement.CELSIUS),
        ("stabilization_fan_work_time", 3, 1, 10, UnitOfMeasurement.MINUTES),
        ("stabilization_temp_delta", 10, 0, 50, UnitOfMeasurement.CELSIUS),
        ("min_fan_power", 31, 30, 50, PERCENTAGE),
        ("min_airflow", 30, 10, 100, PERCENTAGE),
        ("feeder_coefficient", 0.8, 0.1, 2.0, None),
        (
            "fuel_calorific_value",
            5.4,
            0.1,
            25.0,
            UnitOfMeasurement.KILO_WATT_HOUR_PER_KILOGRAM,
        ),
        ("hopper_capacity", 104, 2, 500, UnitOfMeasurement.KILOGRAMS),
        ("heating_target_temp", 60, 60, 80, UnitOfMeasurement.CELSIUS),
        ("min_heating_target_temp", 60, 30, 80, UnitOfMeasurement.CELSIUS),
        ("max_heating_target_temp", 80, 60, 90, UnitOfMeasurement.CELSIUS),
        ("lower_heating_temp_from_thermostat", 5, 0, 30, UnitOfMeasurement.CELSIUS),
        ("water_heater_target_temp", 45, 40, 70, UnitOfMeasurement.CELSIUS),
        ("min_water_heater_target_temp", 40, 20, 55, UnitOfMeasurement.CELSIUS),
        ("max_water_heater_target_temp", 70, 41, 80, UnitOfMeasurement.CELSIUS),
        ("water_heater_work_mode", 0, 0, 2, None),
        ("water_heater_hysteresis", 15, 1, 30, UnitOfMeasurement.CELSIUS),
        ("water_heater_disinfection", STATE_OFF, STATE_OFF, STATE_ON, None),
        ("summer_mode", 0, 0, 2, None),
        ("summer_mode_enable_temp", 15, 5, 30, UnitOfMeasurement.CELSIUS),
        ("summer_mode_disable_temp", 10, 1, 14, UnitOfMeasurement.CELSIUS),
        ("heating_pump_enable_temp", 50, 30, 80, UnitOfMeasurement.CELSIUS),
        ("pause_heating_for_water_heater", 0, 0, 99, UnitOfMeasurement.MINUTES),
        (
            "increase_heating_temp_for_water_heater",
            10,
            3,
            15,
            UnitOfMeasurement.CELSIUS,
        ),
        ("water_heater_work_extension", 5, 0, 99, UnitOfMeasurement.MINUTES),
        ("heat_exchanger", STATE_OFF, STATE_OFF, STATE_ON, None),
        ("weather_control", STATE_ON, STATE_OFF, STATE_ON, None),
        ("heating_curve", 1.7, 0.1, 4.0, None),
        ("boiler_alert_temp", 90, 85, 95, UnitOfMeasurement.CELSIUS),
        ("thermostat_mode", STATE_ON, STATE_OFF, STATE_ON, None),
        ("heating_curve_shift", 0, -20, 20, UnitOfMeasurement.CELSIUS),
        ("low_fuel_level", 10, 5, 99, PERCENTAGE),
        ("fuel_detection_time", 10, 10, 30, UnitOfMeasurement.MINUTES),
        ("feed2_work", 2, 0, 100, UnitOfMeasurement.MINUTES),
        ("fuel_profile", 2, 2, 5, None),
        ("max_feeder_temp", 55, 40, 90, UnitOfMeasurement.CELSIUS),
        ("feeder2_work_time_extension", 4, 0, 250, UnitOfMeasurement.SECONDS),
        ("fuel_type", 0, 0, 1, None),
        ("grate_airflow_power", 30, 30, 100, PERCENTAGE),
        ("grate_fan_work", 4, 0, 100, UnitOfMeasurement.SECONDS),
        ("grate_fan_pause", 8, 1, 250, UnitOfMeasurement.MINUTES),
        ("disable_pump_on_thermostat", STATE_ON, STATE_OFF, STATE_ON, None),
        ("thermostat_operation", 0, 0, 1, None),
        ("max_fuel_flow", 28.6, 0.2, 50.0, UnitOfMeasurement.KILOGRAMS_PER_HOUR),
        ("show_advanced_config", STATE_ON, STATE_OFF, STATE_ON, None),
        ("outdoor_sensor_type", 0, 0, 1, None),
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
    assert len(ecomax.data[ATTR_ECOMAX_SERVICE_PARAMETERS]) == 127

    parameter = ecomax.get_nowait(name)
    assert isinstance(
        parameter,
        EcomaxServiceSwitch if isinstance(value, str) else EcomaxServiceNumber,
    )
    assert equal_parameter_value(parameter.value, value)
    assert equal_parameter_value(parameter.min_value, min_value)
    assert equal_parameter_value(parameter.max_value, max_value)
    assert getattr(parameter, "unit_of_measurement", None) == unit_of_measurement
