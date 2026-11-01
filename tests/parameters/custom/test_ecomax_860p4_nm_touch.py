"""Contains test for ecoMAX 860P4-NM TOUCH custom parameters."""

from __future__ import annotations

from typing import Final

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
from pyplumio.frames.responses import EcomaxExtendedParametersResponse
from pyplumio.parameters import Numeric
from pyplumio.parameters.ecomax import EcomaxExtendedNumber, EcomaxExtendedSwitch
from pyplumio.structures.ecomax_extended_parameters import (
    ATTR_ECOMAX_EXTENDED_PARAMETERS,
)
from pyplumio.structures.product_info import ATTR_PRODUCT, ProductInfo
from tests.conftest import class_from_json, equal_parameter_value

RPM: Final = UnitOfMeasurement.REVOLUTIONS_PER_MINUTE


@pytest.mark.parametrize(
    ("name", "value", "min_value", "max_value", "unit_of_measurement"),
    [
        ("max_boiler_output", 18, 16, 24, UnitOfMeasurement.KILO_WATT),
        ("intermediate_boiler_output", 9, 7, 17, UnitOfMeasurement.KILO_WATT),
        ("min_boiler_output", 6, 6, 8, UnitOfMeasurement.KILO_WATT),
        ("boiler_output_limit", 14, 6, 18, UnitOfMeasurement.KILO_WATT),
        ("fuzzy_logic_a", 5, 2, 8, None),
        ("fuzzy_logic_b", 80, 20, 120, None),
        ("fuzzy_logic_c", 15, 0, 75, None),
        ("fan_speed_30", 1250, 700, 1340, RPM),
        ("fan_speed_50", 1350, 1260, 1690, RPM),
        ("fan_speed_100", 1700, 1360, 2850, RPM),
        ("draft_30", 12, 6, 13, UnitOfMeasurement.PASCAL),
        ("draft_50", 14, 13, 18, UnitOfMeasurement.PASCAL),
        ("draft_100", 19, 15, 255, UnitOfMeasurement.PASCAL),
        ("control_mode", 1, 0, 2, None),
        ("kindling_duration", 9, 1, 20, UnitOfMeasurement.MINUTES),
        ("kindling_fuel_dose", 220, 10, 2550, UnitOfMeasurement.GRAMS),
        ("warming_up_duration", 60, 2, 500, UnitOfMeasurement.SECONDS),
        ("glowing_duration", 2, 0, 100, UnitOfMeasurement.MINUTES),
        ("supervision_duration", 0, 0, 60, UnitOfMeasurement.MINUTES),
        ("supervision_boiler_output", 2.8, 0.2, 51.0, UnitOfMeasurement.KILO_WATT),
        ("supervision_fan_speed", 1150, 700, 2850, RPM),
        ("supervision_draft", 10, 6, 255, UnitOfMeasurement.PASCAL),
        ("max_fan_speed", 2850, 710, 2850, RPM),
        ("min_fan_output", 1, 1, 70, PERCENTAGE),
        ("hopper_capacity", 90, 5, 1275, UnitOfMeasurement.KILOGRAMS),
        ("fan_pi_gain", 30, 0, 255, None),
        ("fan_pi_integral", 10, 0, 255, None),
        ("exhaust_fan_pi_integral", 5, 0, 255, None),
        ("exhaust_fan_pi_gain", 25, 0, 255, None),
        ("stabilization_fan_speed", 1000, 700, 2850, RPM),
        ("stabilization_draft", 30, 6, 255, UnitOfMeasurement.PASCAL),
        ("kindling_fan_speed", 1000, 700, 2850, RPM),
        ("kindling_draft", 40, 6, 255, UnitOfMeasurement.PASCAL),
        ("ignition_test_time", 30, 10, 240, UnitOfMeasurement.SECONDS),
        ("min_fan_speed", 700, 300, 2840, RPM),
        ("min_draft", 6, 0, 100, UnitOfMeasurement.PASCAL),
        ("kindling_temp_delta", 5.0, 0.1, 6.0, UnitOfMeasurement.CELSIUS),
        ("min_burning_off_duration", 3, 1, 20, UnitOfMeasurement.MINUTES),
        ("glowing_fan_speed", 1000, 300, 2850, RPM),
        ("full_power_down_cycles", 4, 0, 10, None),
        ("full_power_up_cycles", 5, 0, 10, None),
        ("fan_power_decrease_delay", 0, 0, 10, None),
        ("kindling_feeding_time", 0.5, 0.1, 3.0, UnitOfMeasurement.SECONDS),
        ("min_boiler_target_temp", 60, 30, 80, UnitOfMeasurement.CELSIUS),
        ("max_boiler_target_temp", 80, 30, 90, UnitOfMeasurement.CELSIUS),
        ("water_heater_pump_mode", 2, 0, 2, None),
        ("heating_pump_start_temp", 45, 30, 80, UnitOfMeasurement.CELSIUS),
        ("heat_exchanger", STATE_ON, STATE_OFF, STATE_ON, None),
        ("thermostat_decrease_boiler_temp", 0, 0, 30, UnitOfMeasurement.CELSIUS),
        ("mixer_1_valve_opening_time", 140, 10, 255, UnitOfMeasurement.SECONDS),
        ("boiler_cooling_temp", 86, 85, 95, UnitOfMeasurement.CELSIUS),
        ("mixer_1_thermostat", STATE_OFF, STATE_OFF, STATE_ON, None),
        ("circulation_pump_pause_time", 30, 0, 255, UnitOfMeasurement.MINUTES),
        ("circulation_pump_work_time", 70, 0, 255, UnitOfMeasurement.SECONDS),
        ("burner_cleaning_interval", 600, 15, 600, UnitOfMeasurement.MINUTES),
        ("burning_off_fan_speed", 1300, 700, 2850, RPM),
        ("burning_off_draft", 30, 6, 255, UnitOfMeasurement.PASCAL),
        ("no_fuel_detection_time", 5, 1, 250, UnitOfMeasurement.MINUTES),
        ("heat_exchanger_cleaning_time", 45, 0, 255, UnitOfMeasurement.SECONDS),
        ("moving_grate_work_time", 27, 10, 250, UnitOfMeasurement.SECONDS),
        ("no_fuel_exhaust_temp", 30, 30, 150, UnitOfMeasurement.CELSIUS),
        ("draft_sensor", STATE_ON, STATE_OFF, STATE_ON, None),
        ("draft_correction", 1, -100, 100, UnitOfMeasurement.PASCAL),
        ("draft_alarm_min", 0, 0, 200, UnitOfMeasurement.PASCAL),
        ("draft_alarm_max", 100, 0, 250, UnitOfMeasurement.PASCAL),
        ("return_protection", 0, 0, 2, None),
        ("min_return_target_temp", 45, 0, 80, UnitOfMeasurement.CELSIUS),
        ("return_temp_hysteresis", 5, 1, 10, UnitOfMeasurement.CELSIUS),
        ("return_valve_closing", 10, 0, 80, PERCENTAGE),
        ("max_fan_output", 100, 30, 100, PERCENTAGE),
        ("h_output_mode", 0, 0, 2, None),
        ("fuel_correction", -20, -20, 20, PERCENTAGE),
        ("airflow_correction", 0, -10, 10, PERCENTAGE),
        ("burning_off_detection_delta_temp", 4, 1, 30, UnitOfMeasurement.CELSIUS),
        ("burning_off_detection_start_temp", 100, 70, 130, UnitOfMeasurement.CELSIUS),
        ("burning_off_detection_end_temp", 55, 30, 95, UnitOfMeasurement.CELSIUS),
        ("grate_cleaning_cycles", 1, 0, 5, None),
    ],
)
@class_from_json(
    EcomaxExtendedParametersResponse,
    "parameters/ecomax_860p4_nm_touch.json",
    arguments=("message",),
)
async def test_custom_parameters(
    ecomax_860p4_nm_touch: EcomaxExtendedParametersResponse,
    ecomax: EcoMAX,
    name: str,
    value: Numeric | State,
    min_value: Numeric | State,
    max_value: Numeric | State,
    unit_of_measurement: UnitOfMeasurement | str | None,
) -> None:
    """Test custom parameters for ecoMAX 860P4-NM TOUCH."""
    await ecomax.dispatch(
        ATTR_PRODUCT,
        ProductInfo(
            type=ProductType.ECOMAX_P,
            id=41,
            uid="*TEST*",
            logo=0,
            image=0,
            model="ecoMAX 860P4-NM TOUCH",
        ),
    )
    ecomax.handle_frame(ecomax_860p4_nm_touch)
    await ecomax.wait_until_done()
    assert len(ecomax.data[ATTR_ECOMAX_EXTENDED_PARAMETERS]) == 231

    parameter = ecomax.get_nowait(name)
    assert isinstance(
        parameter,
        EcomaxExtendedSwitch if isinstance(value, str) else EcomaxExtendedNumber,
    )
    assert equal_parameter_value(parameter.value, value)
    assert equal_parameter_value(parameter.min_value, min_value)
    assert equal_parameter_value(parameter.max_value, max_value)
    assert getattr(parameter, "unit_of_measurement", None) == unit_of_measurement
