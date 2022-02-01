"""Contains constants."""

FRAME_START: int = 0x68
FRAME_END: int = 0x16
HEADER_SIZE: int = 7
BROADCAST_ADDRESS: int = 0x00
ECONET_ADDRESS: int = 0x56
ECONET_TYPE: int = 0x30
ECONET_VERSION: int = 0x05

READER_BUFFER_SIZE: int = 1000
READER_TIMEOUT: int = 5
RECONNECT_TIMEOUT: int = 30

UID_BASE: int = 32
UID_BASE_BITS: int = 5
UID_CHAR_BITS: int = 8

WLAN_ENCRYPTION_UNKNOWN = 0
WLAN_ENCRYPTION_NONE = 1
WLAN_ENCRYPTION_WEP = 2
WLAN_ENCRYPTION_WPA = 3
WLAN_ENCRYPTION_WPA2 = 4
WLAN_ENCRYPTION = (
    WLAN_ENCRYPTION_UNKNOWN,
    WLAN_ENCRYPTION_NONE,
    WLAN_ENCRYPTION_WEP,
    WLAN_ENCRYPTION_WPA,
    WLAN_ENCRYPTION_WPA2,
)

DEFAULT_IP = "0.0.0.0"
DEFAULT_NETMASK = "255.255.255.0"

MODULE_PANEL: str = "module_panel"
MODULE_A: str = "module_a"
MODULE_B: str = "module_b"
MODULE_C: str = "module_c"
MODULE_LAMBDA: str = "module_lambda"
MODULE_ECOSTER: str = "module_ecoster"
MODULES: list = (
    MODULE_PANEL,
    MODULE_A,
    MODULE_B,
    MODULE_C,
    MODULE_LAMBDA,
    MODULE_ECOSTER,
)

MODES: list = (
    "Off",
    "Starting",
    "Kindling",
    "Heating",
    "Supervision",
    "Cooling",
    "Standby",
)

MIXER_TEMP: str = "temp"
MIXER_TARGET: str = "target"
MIXER_PUMP: str = "pump"

ECOSTER_CONTACTS: str = "contacts"
ECOSTER_SCHEDULE: str = "schedule"
ECOSTER_MODE: str = "mode"
ECOSTER_TEMP: str = "temp"
ECOSTER_TARGET: str = "target"

DATA_ALARMS: str = "alarms"
DATA_CO_STATUS: str = "co_status"
DATA_CO_TARGET: str = "co_target"
DATA_CWU_STATUS: str = "cwu_status"
DATA_CWU_TARGET: str = "cwu_target"
DATA_FAN_POWER: str = "fan_power"
DATA_FRAMES: str = "frames"
DATA_FUEL_CONSUMPTION: str = "fuel_consumption"
DATA_FUEL_LEVEL: str = "fuel_level"
DATA_LAMBDA_LEVEL: str = "lambda_level"
DATA_LAMBDA_STATUS: str = "lambda_status"
DATA_LAMBDA_TARGET: str = "lambda_target"
DATA_MIXERS: str = "mixers"
DATA_MODE: str = "mode"
DATA_POWER: str = "power"
DATA_LOAD: str = "load"
DATA_THERMOSTAT: str = "thermostat"
DATA_THERMOSTATS: str = "thermostats"
DATA_TRANSMISSION: str = "transmission"

TEMPERATURES: list = (
    "co_temp",
    "feeder_temp",
    "cwu_temp",
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

OUTPUTS: list = (
    "fan",
    "feeder",
    "co_pump",
    "cwu_pump",
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

DATA_CO_PUMP_FLAG: str = "co_pump_flag"
DATA_CWU_PUMP_FLAG: str = "cwu_pump_flag"
DATA_CIRCULATION_PUMP_FLAG: str = "circulation_pump_flag"
DATA_SOLAR_PUMP_FLAG: str = "solar_pump_flag"
FLAGS: list = (
    DATA_CO_PUMP_FLAG,
    DATA_CWU_PUMP_FLAG,
    DATA_CIRCULATION_PUMP_FLAG,
    DATA_SOLAR_PUMP_FLAG,
)

STATUSES: list = (
    "co_target",
    "co_status",
    "cwu_target",
    "cwu_status",
)

CURRENT_DATA: list = [
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
CURRENT_DATA.extend(TEMPERATURES)
CURRENT_DATA.extend(OUTPUTS)
CURRENT_DATA.extend(FLAGS)
CURRENT_DATA.extend(STATUSES)
CURRENT_DATA.extend(MODULES)

EDITABLE_PARAMS: list = (
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
    "boiler_hysteresis",
    "control_mode",
    "min_fl_power",
    "max_fl_power",
    "min_boiler_power",
    "max_boiler_power",
    "min_fan_power",
    "max_fan_power",
    "t_reduction_airflow",
    "fan_power_gain",
    "fuel_flow_correction_fl",
    "fuel_flow_correction",
    "airflow_correction_100",
    "feeder_correction_100",
    "airflow_correction_50",
    "feeder_correction_50",
    "airflow_correction_30",
    "feeder_correction_30",
    "airflow_power_grate",
    "hist_boiler_grate",
    "supervision_work_airflow",
    "supervision_work_airflow_brake",
    "co_temp_grate",
    "det_time_fuel_grate",
    "airflow_power_kindle",
    "small_airflow_power_kindle",
    "airflow_kindle_delay",
    "scavenge_kindle",
    "feeder_kindle",
    "feeder_kindle_weight",
    "kindle_time",
    "warming_up_time",
    "fumes_temp_kindle_finish",
    "finish_kindle_threshold",
    "fumes_delta_kindle",
    "delta_t_kindle",
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
    "fuel_kg_h",
    "feeder_calibration",
    "fuel_factor",
    "calorific_kwh_kg",
    "fuel_detection_time",
    "fumes_temp_fuel_detection",
    "schedule_feeder_2",
    "feed2_h1",
    "feed2_h2",
    "feed2_h3",
    "feed2_h4",
    "feed2_work",
    "feed2_break",
    "co_set_temp",
    "min_co_set_temp",
    "max_co_set_temp",
    "switch_co_temp",
    "pause_co_cwu",
    "pause_term",
    "work_term",
    "increase_temp_co",
    "program_control_co",
    "co_heat_curve",
    "parallel_co_heat_curve",
    "weather_factor",
    "term_boiler_operation",
    "term_boiler_mode",
    "decrease_set_co_term",
    "term_pump_off",
    "al_boiler_temp",
    "max_feed_temp",
    "extern_boiler_temp",
    "alarm_notif",
    "pump_hysteresis",
    "cwu_set_temp",
    "min_cwu_set_temp",
    "max_cwu_set_temp",
    "cwu_work_mode",
    "cwu_hysteresis",
    "cwu_disinfection",
    "auto_summer",
    "summer_temp_on",
    "summer_temp_off",
    "cwu_feeding_extension",
    "circulation_control",
    "circulation_pause_time",
    "circulation_work_time",
    "circulation_start_temp",
    "buffer_control",
    "buffer_max_temp",
    "min_buffer_temp",
    "buffer_histeresis",
    "buffer_load_start",
    "buffer_load_stop",
    "boiler_control",
)

MIXER_PARAMS: list = (
    "mix_set_temp",
    "min_mix_set_temp",
    "max_mix_set_temp",
    "low_mix_set_temp",
    "ctrl_weather_mix",
    "mix_heat_curve",
    "parallel_offset_heat_curv",
    "weather_temp_factor",
    "mix_operation",
    "mix_insensitivity",
    "mix_therm_operation",
    "mix_therm_mode",
    "mix_off_therm_pump",
    "mix_summer_work",
)
