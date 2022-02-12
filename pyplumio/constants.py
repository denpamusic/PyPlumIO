"""Contains constants."""

from typing import Final, List

from . import data_types

WLAN_ENCRYPTION_UNKNOWN: Final = 0
WLAN_ENCRYPTION_NONE: Final = 1
WLAN_ENCRYPTION_WEP: Final = 2
WLAN_ENCRYPTION_WPA: Final = 3
WLAN_ENCRYPTION_WPA2: Final = 4
WLAN_ENCRYPTION: Final = (
    WLAN_ENCRYPTION_UNKNOWN,
    WLAN_ENCRYPTION_NONE,
    WLAN_ENCRYPTION_WEP,
    WLAN_ENCRYPTION_WPA,
    WLAN_ENCRYPTION_WPA2,
)

DEFAULT_IP: Final = "0.0.0.0"
DEFAULT_NETMASK: Final = "255.255.255.0"

MODULE_PANEL: Final = "module_panel"
MODULE_A: Final = "module_a"
MODULE_B: Final = "module_b"
MODULE_C: Final = "module_c"
MODULE_LAMBDA: Final = "module_lambda"
MODULE_ECOSTER: Final = "module_ecoster"
MODULES: Final = (
    MODULE_A,
    MODULE_B,
    MODULE_C,
    MODULE_LAMBDA,
    MODULE_ECOSTER,
    MODULE_PANEL,
)

MODES: Final = (
    "Off",
    "Starting",
    "Kindling",
    "Heating",
    "Supervision",
    "Cooling",
    "Standby",
)

MIXER_TEMP: Final = "temp"
MIXER_TARGET: Final = "target"
MIXER_PUMP: Final = "pump"
MIXER_DATA: Final = (
    MIXER_TEMP,
    MIXER_TARGET,
    MIXER_PUMP,
)

ECOSTER_CONTACTS: Final = "contacts"
ECOSTER_SCHEDULE: Final = "schedule"
ECOSTER_MODE: Final = "mode"
ECOSTER_TEMP: Final = "temp"
ECOSTER_TARGET: Final = "target"

DATA_ALARMS: Final = "alarms"
DATA_FAN_POWER: Final = "fan_power"
DATA_FRAMES: Final = "frames"
DATA_FUEL_CONSUMPTION: Final = "fuel_consumption"
DATA_FUEL_LEVEL: Final = "fuel_level"
DATA_LAMBDA_LEVEL: Final = "lambda_level"
DATA_LAMBDA_STATUS: Final = "lambda_status"
DATA_LAMBDA_TARGET: Final = "lambda_target"
DATA_MIXERS: Final = "mixers"
DATA_MODE: Final = "mode"
DATA_POWER: Final = "power"
DATA_LOAD: Final = "load"
DATA_THERMOSTAT: Final = "thermostat"
DATA_THERMOSTATS: Final = "thermostats"
DATA_TRANSMISSION: Final = "transmission"

TEMPERATURES: Final = (
    "heating_temp",
    "feeder_temp",
    "water_heater_temp",
    "outside_temp",
    "back_temp",
    "exhaust_temp",
    "optical_temp",
    "upper_buffer_temp",
    "lower_buffer_temp",
    "upper_solar_temp",
    "lower_solar_temp",
    "fireplace_temp",
    "total_gain",
    "hydraulic_coupler_temp",
    "exchanger_temp",
    "air_in_temp",
    "air_out_temp",
)

OUTPUTS: Final = (
    "fan",
    "feeder",
    "heating_pump",
    "water_heater_pump",
    "ciculation_pump",
    "lighter",
    "alarm",
    "outer_boiler",
    "fan2_exhaust",
    "feeder2",
    "outer_feeder",
    "solar_pump",
    "fireplace_pump",
    "gcz_contact",
    "blow_fan1",
    "blow_fan2",
)

DATA_HEATING_PUMP_FLAG: Final = "heating_pump_flag"
DATA_WATER_HEATER_PUMP_FLAG: Final = "water_heater_pump_flag"
DATA_CIRCULATION_PUMP_FLAG: Final = "circulation_pump_flag"
DATA_SOLAR_PUMP_FLAG: Final = "solar_pump_flag"
FLAGS: Final = (
    DATA_HEATING_PUMP_FLAG,
    DATA_WATER_HEATER_PUMP_FLAG,
    DATA_CIRCULATION_PUMP_FLAG,
    DATA_SOLAR_PUMP_FLAG,
)

DATA_HEATING_TARGET: Final = "heating_target"
DATA_HEATING_STATUS: Final = "heating_status"
DATA_WATER_HEATER_TARGET: Final = "water_heater_target"
DATA_WATER_HEATER_STATUS: Final = "water_heater_status"
STATUSES: Final = (
    DATA_HEATING_TARGET,
    DATA_HEATING_STATUS,
    DATA_WATER_HEATER_TARGET,
    DATA_WATER_HEATER_STATUS,
)

DEVICE_DATA: List[str] = [
    DATA_ALARMS,
    DATA_FAN_POWER,
    DATA_FRAMES,
    DATA_FUEL_CONSUMPTION,
    DATA_FUEL_LEVEL,
    DATA_LAMBDA_LEVEL,
    DATA_LAMBDA_STATUS,
    DATA_LAMBDA_TARGET,
    DATA_LOAD,
    DATA_MODE,
    DATA_POWER,
    DATA_THERMOSTAT,
    DATA_THERMOSTATS,
    DATA_TRANSMISSION,
]
DEVICE_DATA.extend(TEMPERATURES)
DEVICE_DATA.extend(OUTPUTS)
DEVICE_DATA.extend(FLAGS)
DEVICE_DATA.extend(STATUSES)
DEVICE_DATA.extend(MODULES)

DEVICE_PARAMS: Final = (
    "airflow_power_100",
    "airflow_power_50",
    "airflow_power_30",
    "power_100",
    "power_50",
    "power_30",
    "max_fan_boiler_power",
    "min_fan_boiler_power",
    "fuel_feeding_time_100",
    "fuel_feeding_time_50",
    "fuel_feeding_time_30",
    "fuel_feeding_break_100",
    "fuel_feeding_break_50",
    "fuel_feeding_break_30",
    "cycle_time",
    "h2_hysteresis",
    "h1_hysteresis",
    "heating_hysteresis",
    "fuzzy_logic",
    "min_fuzzy_logic_power",
    "max_fuzzy_logic_power",
    "min_boiler_power",
    "max_boiler_power",
    "min_fan_power",
    "max_fan_power",
    "t_reduction_airflow",
    "fan_power_gain",
    "fuel_flow_correction_fuzzy_logic",
    "fuel_flow_correction",
    "airflow_correction_100",
    "feeder_correction_100",
    "airflow_correction_50",
    "feeder_correction_50",
    "airflow_correction_30",
    "feeder_correction_30",
    "airflow_power_grate",
    "boiler_hysteresis_grate",
    "supervision_work_airflow",
    "supervision_work_airflow_brake",
    "heating_temp_grate",
    "fuel_detection_time_grate",
    "airflow_power_kindle",
    "small_airflow_power_kindle",
    "airflow_kindle_delay",
    "scavenge_kindle",
    "feeder_kindle",
    "feeder_kindle_weight",
    "kindle_time",
    "warming_up_time",
    "kindle_finish_fumes_temp",
    "kindle_finish_threshold",
    "kindle_fumes_delta_temp",
    "kindle_delta_t",
    "min_kindle_power_time",
    "scavenge_after_kindle",
    "airflow_power_after_kindle",
    "supervision_time",
    "feed_time_supervision",
    "feed_time_supervision_weight",
    "feed_supervision_break",
    "supervision_cycle_duration",
    "airflow_power_supervision",
    "fan_supervison_break",
    "fan_work_supervision",
    "increase_fan_support_mode",
    "max_extinguish_time",
    "min_extinguish_time",
    "extinguish_time",
    "airflow_power_extinguish",
    "airflow_work_extinguish",
    "airflow_brake_extinguish",
    "scavenge_start_extinguish",
    "scavenge_stop_extinguish",
    "clean_begin_time",
    "extinguish_clean_time",
    "airflow_power_clean",
    "warming_up_brake_time",
    "warming_up_cycle_time",
    "remind_time",
    "lambda_work",
    "lambda_correction_range",
    "oxygen_100",
    "oxygen_50",
    "oxygen_30",
    "oxygen_correction_fl",
    "fuel_flow_kg_h",
    "feeder_calibration",
    "fuel_factor",
    "fuel_energy_kwh_kg",
    "fuel_detection_time",
    "fuel_detection_fumes_temp",
    "schedule_feeder_2",
    "feed2_h1",
    "feed2_h2",
    "feed2_h3",
    "feed2_h4",
    "feed2_work",
    "feed2_break",
    "heating_set_temp",
    "min_heating_set_temp",
    "max_heating_set_temp",
    "heating_pump_on_temp",
    "pause_heating_for_water_heater",
    "pause_term",
    "work_term",
    "increase_heating_temp_for_water_heater",
    "heating_weather_control",
    "heating_heat_curve",
    "heating_heat_curve_shift",
    "weather_factor",
    "term_boiler_operation",
    "term_boiler_mode",
    "decrease_set_heating_term",
    "term_pump_off",
    "al_boiler_temp",
    "max_feeder_temp",
    "external_boiler_temp",
    "alarm_notify",
    "pump_hysteresis",
    "water_heater_set_temp",
    "min_water_heater_set_temp",
    "max_water_heater_set_temp",
    "water_heater_work_mode",
    "water_heater_hysteresis",
    "water_heater_disinfection",
    "summer_mode",
    "summer_mode_on_temp",
    "summer_mode_off_temp",
    "water_heater_feeding_extension",
    "circulation_control",
    "circulation_pause_time",
    "circulation_work_time",
    "circulation_start_temp",
    "buffer_control",
    "max_buffer_temp",
    "min_buffer_temp",
    "buffer_histeresis",
    "buffer_load_start",
    "buffer_load_stop",
    "boiler_control",
)

MIXER_PARAMS: Final = (
    "mix_set_temp",
    "min_mix_set_temp",
    "max_mix_set_temp",
    "low_mix_set_temp",
    "ctrl_weather_mix",
    "mix_heat_curve",
    "parallel_offset_heat_curve",
    "weather_temp_factor",
    "mix_operation",
    "mix_insensitivity",
    "mix_therm_operation",
    "mix_therm_mode",
    "mix_off_therm_pump",
    "mix_summer_work",
)

DATA_TYPES: Final = (
    data_types.Undefined0,
    data_types.SignedChar,
    data_types.Short,
    data_types.Int,
    data_types.Byte,
    data_types.UnsignedShort,
    data_types.UnsignedInt,
    data_types.Float,
    data_types.Undefined8,
    data_types.Double,
    data_types.Boolean,
    data_types.String,
    data_types.String,
    data_types.Int64,
    data_types.UInt64,
    data_types.IPv4,
    data_types.IPv6,
)

REGDATA_SCHEMA: Final = {
    1792: DATA_MODE,
    1024: TEMPERATURES[0],
    1026: TEMPERATURES[1],
    1025: TEMPERATURES[2],
    1027: TEMPERATURES[3],
    1030: TEMPERATURES[5],
    1280: DATA_HEATING_TARGET,
    1281: DATA_WATER_HEATER_TARGET,
    1536: OUTPUTS[0],
    1538: OUTPUTS[1],
    1541: OUTPUTS[2],
    1542: OUTPUTS[3],
    3: OUTPUTS[5],
}
