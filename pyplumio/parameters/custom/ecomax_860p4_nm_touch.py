"""Contains custom parameters for ecoMAX 860P4-NM TOUCH."""

from __future__ import annotations

from functools import partial

from pyplumio.parameters.custom import custom_parameters, number, switch

# Fan speed is stored as (rpm - 300) / 10.
_fan_speed = partial(number, step=10.0, offset=-30, unit="rpm")

PARAMETERS = custom_parameters(
    model="ecoMAX 860P4-NM TOUCH",
    id=41,
    service_parameters={
        0: number("max_boiler_output", unit="kW"),
        1: number("intermediate_boiler_output", unit="kW"),
        2: number("min_boiler_output", unit="kW"),
        3: number("boiler_output_limit", unit="kW"),
        8: number("fuzzy_logic_a"),
        9: number("fuzzy_logic_b"),
        10: number("fuzzy_logic_c"),
        11: _fan_speed("fan_speed_30"),
        12: _fan_speed("fan_speed_50"),
        13: _fan_speed("fan_speed_100"),
        17: number("draft_30", unit="Pa"),
        18: number("draft_50", unit="Pa"),
        19: number("draft_100", unit="Pa"),
        # 0 - standard, 1 - fuzzy logic. Kept as a number, because the
        # controller allows a third value (2) with unknown meaning.
        23: number("control_mode"),
        24: number("kindling_duration", unit="min"),
        25: number("kindling_fuel_dose", step=10.0, unit="g"),
        26: number("warming_up_duration", step=2.0, unit="s"),
        27: number("glowing_duration", unit="min"),
        28: number("supervision_duration", unit="min"),
        29: number("supervision_boiler_output", step=0.2, unit="kW"),
        32: _fan_speed("supervision_fan_speed"),
        34: number("supervision_draft", unit="Pa"),
        35: _fan_speed("max_fan_speed"),
        36: number("min_fan_output", unit="%"),
        53: number("hopper_capacity", step=5.0, unit="kg"),
        54: number("fan_pi_gain"),
        55: number("fan_pi_integral"),
        56: number("exhaust_fan_pi_integral"),
        57: number("exhaust_fan_pi_gain"),
        59: _fan_speed("stabilization_fan_speed"),
        61: number("stabilization_draft", unit="Pa"),
        63: _fan_speed("kindling_fan_speed"),
        65: number("kindling_draft", unit="Pa"),
        66: number("ignition_test_time", unit="s"),
        70: _fan_speed("min_fan_speed"),
        71: number("min_draft", unit="Pa"),
        72: number("kindling_temp_delta", step=0.1, unit="°C"),
        73: number("min_burning_off_duration", unit="min"),
        75: _fan_speed("glowing_fan_speed"),
        76: number("full_power_down_cycles"),
        77: number("full_power_up_cycles"),
        78: number("fan_power_decrease_delay"),
        80: number("kindling_feeding_time", step=0.1, unit="s"),
        85: number("min_boiler_target_temp", unit="°C"),
        86: number("max_boiler_target_temp", unit="°C"),
        # 0 - off, 1 - priority, 2 - no priority.
        90: number("water_heater_pump_mode"),
        96: number("heating_pump_start_temp", unit="°C"),
        100: switch("heat_exchanger"),
        117: number("thermostat_decrease_boiler_temp", unit="°C"),
        143: number("mixer_1_valve_opening_time", unit="s"),
        155: number("boiler_cooling_temp", unit="°C"),
        157: switch("mixer_1_thermostat"),
        162: number("circulation_pump_pause_time", unit="min"),
        163: number("circulation_pump_work_time", unit="s"),
        176: number("burner_cleaning_interval", step=15.0, unit="min"),
        178: _fan_speed("burning_off_fan_speed"),
        180: number("burning_off_draft", unit="Pa"),
        187: number("no_fuel_detection_time", unit="min"),
        195: number("heat_exchanger_cleaning_time", unit="s"),
        196: number("moving_grate_work_time", unit="s"),
        201: number("no_fuel_exhaust_temp", unit="°C"),
        205: switch("draft_sensor"),
        207: number("draft_correction", offset=100, unit="Pa"),
        208: number("draft_alarm_min", unit="Pa"),
        209: number("draft_alarm_max", unit="Pa"),
        # 0 - off, 1 - 4D valve, 2 - 3D valve (by panel list order).
        210: number("return_protection"),
        211: number("min_return_target_temp", unit="°C"),
        212: number("return_temp_hysteresis", unit="°C"),
        213: number("return_valve_closing", unit="%"),
        214: number("max_fan_output", unit="%"),
        # 0 - reserve boiler, 1 - alarms, 2 - circulation pump.
        215: number("h_output_mode"),
        220: number("fuel_correction", offset=20, unit="%"),
        221: number("airflow_correction", offset=10, unit="%"),
        222: number("burning_off_detection_delta_temp", unit="°C"),
        223: number("burning_off_detection_start_temp", unit="°C"),
        224: number("burning_off_detection_end_temp", unit="°C"),
        227: number("grate_cleaning_cycles"),
    },
)
