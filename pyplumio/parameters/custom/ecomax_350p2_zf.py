"""Contains patch for ecoMAX 350P2-ZF."""

from __future__ import annotations

from pyplumio.const import PERCENTAGE, UnitOfMeasurement
from pyplumio.parameters.custom import CustomParameters, Signature
from pyplumio.parameters.ecomax import EcomaxNumberDescription, EcomaxSwitchDescription


class EcoMAX350P2ZF(CustomParameters):
    """Custom parameters for ecoMAX 350P2-ZF."""

    signature = Signature(model="ecoMAX 350P2-ZF", id=90)

    descriptions = {
        # [overrides standard]
        0: EcomaxNumberDescription(
            name="boiler_power_100",
            unit_of_measurement=UnitOfMeasurement.KILO_WATT,
        ),
        # [overrides standard]
        1: EcomaxNumberDescription(
            name="boiler_power_50",
            unit_of_measurement=UnitOfMeasurement.KILO_WATT,
        ),
        # [overrides standard]
        2: EcomaxNumberDescription(
            name="boiler_power_30",
            unit_of_measurement=UnitOfMeasurement.KILO_WATT,
        ),
        # [overrides standard]
        3: EcomaxNumberDescription(
            name="airflow_power_100",
            unit_of_measurement=PERCENTAGE,
        ),
        # [overrides standard]
        4: EcomaxNumberDescription(
            name="airflow_power_50",
            unit_of_measurement=PERCENTAGE,
        ),
        # [overrides standard]
        5: EcomaxNumberDescription(
            name="airflow_power_30",
            unit_of_measurement=PERCENTAGE,
        ),
        # [overrides standard]
        6: EcomaxNumberDescription(
            name="h2_hysteresis",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        # [overrides standard]
        7: EcomaxNumberDescription(
            name="h1_hysteresis",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        # [overrides standard]
        8: EcomaxNumberDescription(
            name="heating_hysteresis",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        # [overrides standard]
        9: EcomaxNumberDescription(
            name="cycle_duration",
            unit_of_measurement=UnitOfMeasurement.SECONDS,
        ),
        # [overrides standard]
        10: EcomaxNumberDescription(
            name="min_fuzzy_logic_power",
            unit_of_measurement=PERCENTAGE,
        ),
        # [overrides standard]
        11: EcomaxNumberDescription(
            name="max_fuzzy_logic_power",
            unit_of_measurement=PERCENTAGE,
        ),
        12: EcomaxNumberDescription(name="fuzzy_logic_parameter_a"),
        13: EcomaxNumberDescription(name="fuzzy_logic_parameter_b"),
        14: EcomaxNumberDescription(name="fuzzy_logic_parameter_c"),
        16: EcomaxNumberDescription(
            name="kindling_fan_power",
            unit_of_measurement=PERCENTAGE,
        ),
        17: EcomaxNumberDescription(
            name="kindling_fuel_detection_time",
            unit_of_measurement=UnitOfMeasurement.SECONDS,
        ),
        # [overrides standard]
        18: EcomaxNumberDescription(
            name="kindling_time",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        19: EcomaxNumberDescription(
            name="kindling_fuel_dose",
            step=10,
            unit_of_measurement=UnitOfMeasurement.GRAMS,
        ),
        20: EcomaxNumberDescription(
            name="kindling_flue_gas_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        21: EcomaxNumberDescription(
            name="kindling_low_power_time",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        22: EcomaxNumberDescription(
            name="stabilization_fan_power",
            unit_of_measurement=PERCENTAGE,
        ),
        23: EcomaxNumberDescription(
            name="stabilization_min_flue_gas_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        24: EcomaxNumberDescription(
            name="stabilization_fan_work_time",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        25: EcomaxNumberDescription(
            name="stabilization_temp_delta",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        # [overrides standard]
        33: EcomaxNumberDescription(
            name="min_fan_power",
            unit_of_measurement=PERCENTAGE,
        ),
        39: EcomaxNumberDescription(name="feeder_coefficient", step=0.1),
        # [overrides standard]
        40: EcomaxNumberDescription(
            name="fuel_calorific_value",
            step=0.1,
            unit_of_measurement=UnitOfMeasurement.KILO_WATT_HOUR_PER_KILOGRAM,
        ),
        41: EcomaxNumberDescription(
            name="hopper_capacity",
            step=2,
            unit_of_measurement=UnitOfMeasurement.KILOGRAMS,
        ),
        # [overrides standard]
        44: EcomaxNumberDescription(
            name="heating_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        # [overrides standard]
        45: EcomaxNumberDescription(
            name="min_heating_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        # [overrides standard]
        46: EcomaxNumberDescription(
            name="max_heating_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        47: EcomaxNumberDescription(
            name="lower_heating_temp_from_thermostat",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        # [overrides standard]
        48: EcomaxNumberDescription(
            name="water_heater_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        # [overrides standard]
        49: EcomaxNumberDescription(
            name="min_water_heater_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        # [overrides standard]
        50: EcomaxNumberDescription(
            name="max_water_heater_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        # [overrides standard]
        # 0 - off, 1 - priority, 2 - non-priority
        51: EcomaxNumberDescription(name="water_heater_work_mode"),
        # [overrides standard]
        52: EcomaxNumberDescription(
            name="water_heater_hysteresis",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        # [overrides standard]
        53: EcomaxSwitchDescription(name="water_heater_disinfection"),
        # [overrides standard]
        # 0 - winter, 1 - summer, 2 - auto
        54: EcomaxNumberDescription(name="summer_mode"),
        # [overrides standard]
        55: EcomaxNumberDescription(
            name="summer_mode_enable_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        # [overrides standard]
        56: EcomaxNumberDescription(
            name="summer_mode_disable_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        # [overrides standard]
        57: EcomaxNumberDescription(
            name="heating_pump_enable_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        # [overrides standard]
        58: EcomaxNumberDescription(
            name="pause_heating_for_water_heater",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        # [overrides standard]
        59: EcomaxNumberDescription(
            name="increase_heating_temp_for_water_heater",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        # [overrides standard]
        60: EcomaxNumberDescription(
            name="water_heater_work_extension",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        61: EcomaxSwitchDescription(name="heat_exchanger"),
        # [overrides standard]
        84: EcomaxSwitchDescription(name="weather_control"),
        # [overrides standard]
        85: EcomaxNumberDescription(name="heating_curve", step=0.1),
        # [overrides standard]
        86: EcomaxNumberDescription(
            name="boiler_alert_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        # [overrides standard]
        87: EcomaxSwitchDescription(name="thermostat_mode"),
        # [overrides standard]
        92: EcomaxNumberDescription(
            name="heating_curve_shift",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
            offset=20,
        ),
        101: EcomaxNumberDescription(
            name="low_fuel_level",
            unit_of_measurement=PERCENTAGE,
        ),
        # 0 - 100%, 1 - 0%, 2 - in progress
        102: EcomaxNumberDescription(name="fuel_level_calibration"),
        # [overrides standard]
        103: EcomaxNumberDescription(
            name="fuel_detection_time",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        # [overrides standard]
        106: EcomaxNumberDescription(
            name="feed2_work",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        # 2 - white pellets, 3 - brown pellets
        109: EcomaxNumberDescription(name="fuel_profile"),
        # [overrides standard]
        110: EcomaxNumberDescription(
            name="max_feeder_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        111: EcomaxNumberDescription(
            name="feeder2_work_time_extension",
            unit_of_measurement=UnitOfMeasurement.SECONDS,
        ),
        # 0 - pellets, 1 - wood
        113: EcomaxNumberDescription(name="fuel_type"),
        # [overrides standard]
        116: EcomaxNumberDescription(
            name="grate_airflow_power",
            unit_of_measurement=PERCENTAGE,
        ),
        # [overrides standard]
        118: EcomaxNumberDescription(
            name="grate_fan_work",
            unit_of_measurement=UnitOfMeasurement.SECONDS,
        ),
        # [overrides standard]
        119: EcomaxNumberDescription(
            name="grate_fan_pause",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        # [overrides standard]
        120: EcomaxSwitchDescription(name="disable_pump_on_thermostat"),
        # [overrides standard]
        121: EcomaxNumberDescription(name="thermostat_operation"),
        # [overrides standard]
        122: EcomaxNumberDescription(
            name="max_fuel_flow",
            step=0.2,
            unit_of_measurement=UnitOfMeasurement.KILOGRAMS_PER_HOUR,
        ),
        125: EcomaxSwitchDescription(name="show_advanced_config"),
        # 0 - CT6-P, 1 - CT4-P
        126: EcomaxNumberDescription(name="outdoor_sensor_type"),
    }
