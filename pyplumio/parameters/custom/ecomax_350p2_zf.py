"""Contains patch for ecoMAX 350P2-ZF."""

from __future__ import annotations

from pyplumio.const import PERCENTAGE, UnitOfMeasurement
from pyplumio.parameters.custom import CustomParameters, Signature
from pyplumio.parameters.ecomax import EcomaxNumberDescription, EcomaxSwitchDescription


class EcoMAX350P2ZF(CustomParameters):
    """Custom parameters for ecoMAX 350P2-ZF."""

    signature = Signature(model="ecoMAX 350P2-ZF", id=90)

    descriptions = {
        8: EcomaxNumberDescription(
            name="heating_cycle_time",
            unit_of_measurement=UnitOfMeasurement.SECONDS,
        ),
        12: EcomaxNumberDescription(name="fuzzy_logic_parameter_a"),
        13: EcomaxNumberDescription(name="fuzzy_logic_parameter_b"),
        14: EcomaxNumberDescription(name="fuzzy_logic_parameter_c"),
        16: EcomaxNumberDescription(
            name="ignition_fan_power", unit_of_measurement=PERCENTAGE
        ),
        17: EcomaxNumberDescription(
            name="ignition_fuel_detection_time",
            unit_of_measurement=UnitOfMeasurement.SECONDS,
        ),
        19: EcomaxNumberDescription(
            name="ignition_fuel_dose",
            step=10,
            unit_of_measurement=UnitOfMeasurement.GRAMS,
        ),
        20: EcomaxNumberDescription(
            name="ignition_flue_gas_temp", unit_of_measurement=UnitOfMeasurement.CELSIUS
        ),
        21: EcomaxNumberDescription(
            name="ignition_low_power_time",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        22: EcomaxNumberDescription(
            name="stabilization_fan_power", unit_of_measurement=PERCENTAGE
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
        28: EcomaxNumberDescription(
            name="min_fan_power", unit_of_measurement=PERCENTAGE
        ),
        39: EcomaxNumberDescription(name="feeder_coefficient", step=0.1),
        41: EcomaxNumberDescription(
            name="hopper_capacity",
            step=2,
            unit_of_measurement=UnitOfMeasurement.KILOGRAMS,
        ),
        47: EcomaxNumberDescription(
            name="lower_heating_temp_from_thermostat",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        86: EcomaxNumberDescription(
            name="boiler_alert_temp", unit_of_measurement=UnitOfMeasurement.CELSIUS
        ),
        87: EcomaxSwitchDescription(name="thermostat_mode"),
        111: EcomaxNumberDescription(
            name="feeder2_work_time_extension",
            unit_of_measurement=UnitOfMeasurement.SECONDS,
        ),
        # 0 - pellets, 1 - wood
        113: EcomaxNumberDescription(name="fuel_type"),
    }
