"""Contains regulator parameter structure parser."""

from typing import Any, Dict, Final, List, Tuple

from pyplumio import util

PARAMETER_BOILER_CONTROL: Final = "boiler_control"
DEVICE_PARAMETERS: List[str] = [
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
]


def from_bytes(
    message: bytearray, offset: int = 0, data: Dict[str, Any] = None
) -> Tuple[Dict[str, Any], int]:
    """Parses frame message into usable data.

    Keyword arguments:
        message -- message bytes
        offset -- current data offset
    """
    if data is None:
        data = {}

    first_parameter = message[1]
    parameters_number = message[2]
    offset = 3
    if parameters_number == 0:
        return data, offset

    for index in range(first_parameter, parameters_number + first_parameter):
        parameter = util.unpack_parameter(message, offset)
        if parameter is not None:
            data[DEVICE_PARAMETERS[index]] = parameter

        offset += 3

    return data, offset
