"""Contains patch for ecoMAX 860P4-NM TOUCH."""

from __future__ import annotations

from functools import partial

from pyplumio.const import PERCENTAGE, UnitOfMeasurement
from pyplumio.parameters.custom import CustomParameters, Signature
from pyplumio.parameters.ecomax import EcomaxNumberDescription, EcomaxSwitchDescription

# Fan speed is stored as (rpm - 300) / 10.
_fan_speed_description = partial(
    EcomaxNumberDescription,
    step=10.0,
    offset=-30,
    unit_of_measurement=UnitOfMeasurement.REVOLUTIONS_PER_MINUTE,
)


class EcoMAX860P4NMTOUCH(CustomParameters):
    """Custom parameters for ecoMAX 860P4-NM TOUCH."""

    signature = Signature(model="ecoMAX 860P4-NM TOUCH", id=41)

    extended = {
        0: EcomaxNumberDescription(
            name="max_boiler_output",
            unit_of_measurement=UnitOfMeasurement.KILO_WATT,
        ),
        1: EcomaxNumberDescription(
            name="intermediate_boiler_output",
            unit_of_measurement=UnitOfMeasurement.KILO_WATT,
        ),
        2: EcomaxNumberDescription(
            name="min_boiler_output",
            unit_of_measurement=UnitOfMeasurement.KILO_WATT,
        ),
        3: EcomaxNumberDescription(
            name="boiler_output_limit",
            unit_of_measurement=UnitOfMeasurement.KILO_WATT,
        ),
        8: EcomaxNumberDescription(
            name="fuzzy_logic_a",
        ),
        9: EcomaxNumberDescription(
            name="fuzzy_logic_b",
        ),
        10: EcomaxNumberDescription(
            name="fuzzy_logic_c",
        ),
        11: _fan_speed_description("fan_speed_30"),
        12: _fan_speed_description("fan_speed_50"),
        13: _fan_speed_description("fan_speed_100"),
        17: EcomaxNumberDescription(
            name="draft_30",
            unit_of_measurement=UnitOfMeasurement.PASCAL,
        ),
        18: EcomaxNumberDescription(
            name="draft_50",
            unit_of_measurement=UnitOfMeasurement.PASCAL,
        ),
        19: EcomaxNumberDescription(
            name="draft_100",
            unit_of_measurement=UnitOfMeasurement.PASCAL,
        ),
        # 0 - standard, 1 - fuzzy logic. Kept as a number, because the
        # controller allows a third value (2) with unknown meaning.
        23: EcomaxNumberDescription(
            name="control_mode",
        ),
        24: EcomaxNumberDescription(
            name="kindling_duration",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        25: EcomaxNumberDescription(
            name="kindling_fuel_dose",
            step=10.0,
            unit_of_measurement=UnitOfMeasurement.GRAMS,
        ),
        26: EcomaxNumberDescription(
            name="warming_up_duration",
            step=2.0,
            unit_of_measurement=UnitOfMeasurement.SECONDS,
        ),
        27: EcomaxNumberDescription(
            name="glowing_duration",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        28: EcomaxNumberDescription(
            name="supervision_duration",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        29: EcomaxNumberDescription(
            name="supervision_boiler_output",
            step=0.2,
            unit_of_measurement=UnitOfMeasurement.KILO_WATT,
        ),
        32: _fan_speed_description("supervision_fan_speed"),
        34: EcomaxNumberDescription(
            name="supervision_draft",
            unit_of_measurement=UnitOfMeasurement.PASCAL,
        ),
        35: _fan_speed_description("max_fan_speed"),
        36: EcomaxNumberDescription(
            name="min_fan_output",
            unit_of_measurement=PERCENTAGE,
        ),
        53: EcomaxNumberDescription(
            name="hopper_capacity",
            step=5.0,
            unit_of_measurement=UnitOfMeasurement.KILOGRAMS,
        ),
        54: EcomaxNumberDescription(
            name="fan_pi_gain",
        ),
        55: EcomaxNumberDescription(
            name="fan_pi_integral",
        ),
        56: EcomaxNumberDescription(
            name="exhaust_fan_pi_integral",
        ),
        57: EcomaxNumberDescription(
            name="exhaust_fan_pi_gain",
        ),
        59: _fan_speed_description("stabilization_fan_speed"),
        61: EcomaxNumberDescription(
            name="stabilization_draft",
            unit_of_measurement=UnitOfMeasurement.PASCAL,
        ),
        63: _fan_speed_description("kindling_fan_speed"),
        65: EcomaxNumberDescription(
            name="kindling_draft",
            unit_of_measurement=UnitOfMeasurement.PASCAL,
        ),
        66: EcomaxNumberDescription(
            name="ignition_test_time",
            unit_of_measurement=UnitOfMeasurement.SECONDS,
        ),
        70: _fan_speed_description("min_fan_speed"),
        71: EcomaxNumberDescription(
            name="min_draft",
            unit_of_measurement=UnitOfMeasurement.PASCAL,
        ),
        72: EcomaxNumberDescription(
            name="kindling_temp_delta",
            step=0.1,
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        73: EcomaxNumberDescription(
            name="min_burning_off_duration",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        75: _fan_speed_description("glowing_fan_speed"),
        76: EcomaxNumberDescription(
            name="full_power_down_cycles",
        ),
        77: EcomaxNumberDescription(
            name="full_power_up_cycles",
        ),
        78: EcomaxNumberDescription(
            name="fan_power_decrease_delay",
        ),
        80: EcomaxNumberDescription(
            name="kindling_feeding_time",
            step=0.1,
            unit_of_measurement=UnitOfMeasurement.SECONDS,
        ),
        85: EcomaxNumberDescription(
            name="min_boiler_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        86: EcomaxNumberDescription(
            name="max_boiler_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        # 0 - off, 1 - priority, 2 - no priority.
        90: EcomaxNumberDescription(
            name="water_heater_pump_mode",
        ),
        96: EcomaxNumberDescription(
            name="heating_pump_start_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        100: EcomaxSwitchDescription(
            name="heat_exchanger",
        ),
        117: EcomaxNumberDescription(
            name="thermostat_decrease_boiler_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        143: EcomaxNumberDescription(
            name="mixer_1_valve_opening_time",
            unit_of_measurement=UnitOfMeasurement.SECONDS,
        ),
        155: EcomaxNumberDescription(
            name="boiler_cooling_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        157: EcomaxSwitchDescription(
            name="mixer_1_thermostat",
        ),
        162: EcomaxNumberDescription(
            name="circulation_pump_pause_time",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        163: EcomaxNumberDescription(
            name="circulation_pump_work_time",
            unit_of_measurement=UnitOfMeasurement.SECONDS,
        ),
        176: EcomaxNumberDescription(
            name="burner_cleaning_interval",
            step=15.0,
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        178: _fan_speed_description("burning_off_fan_speed"),
        180: EcomaxNumberDescription(
            name="burning_off_draft",
            unit_of_measurement=UnitOfMeasurement.PASCAL,
        ),
        187: EcomaxNumberDescription(
            name="no_fuel_detection_time",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        195: EcomaxNumberDescription(
            name="heat_exchanger_cleaning_time",
            unit_of_measurement=UnitOfMeasurement.SECONDS,
        ),
        196: EcomaxNumberDescription(
            name="moving_grate_work_time",
            unit_of_measurement=UnitOfMeasurement.SECONDS,
        ),
        201: EcomaxNumberDescription(
            name="no_fuel_exhaust_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        205: EcomaxSwitchDescription(
            name="draft_sensor",
        ),
        207: EcomaxNumberDescription(
            name="draft_correction",
            offset=100,
            unit_of_measurement=UnitOfMeasurement.PASCAL,
        ),
        208: EcomaxNumberDescription(
            name="draft_alarm_min",
            unit_of_measurement=UnitOfMeasurement.PASCAL,
        ),
        209: EcomaxNumberDescription(
            name="draft_alarm_max",
            unit_of_measurement=UnitOfMeasurement.PASCAL,
        ),
        # 0 - off, 1 - 4D valve, 2 - 3D valve (by panel list order).
        210: EcomaxNumberDescription(
            name="return_protection",
        ),
        211: EcomaxNumberDescription(
            name="min_return_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        212: EcomaxNumberDescription(
            name="return_temp_hysteresis",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        213: EcomaxNumberDescription(
            name="return_valve_closing",
            unit_of_measurement=PERCENTAGE,
        ),
        214: EcomaxNumberDescription(
            name="max_fan_output",
            unit_of_measurement=PERCENTAGE,
        ),
        # 0 - reserve boiler, 1 - alarms, 2 - circulation pump.
        215: EcomaxNumberDescription(
            name="h_output_mode",
        ),
        220: EcomaxNumberDescription(
            name="fuel_correction",
            offset=20,
            unit_of_measurement=PERCENTAGE,
        ),
        221: EcomaxNumberDescription(
            name="airflow_correction",
            offset=10,
            unit_of_measurement=PERCENTAGE,
        ),
        222: EcomaxNumberDescription(
            name="burning_off_detection_delta_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        223: EcomaxNumberDescription(
            name="burning_off_detection_start_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        224: EcomaxNumberDescription(
            name="burning_off_detection_end_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        227: EcomaxNumberDescription(
            name="grate_cleaning_cycles",
        ),
    }
