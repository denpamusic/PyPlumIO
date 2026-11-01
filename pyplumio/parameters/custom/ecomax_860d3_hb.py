"""Contains patch for ecoMAX 860D3-HB."""

from __future__ import annotations

from pyplumio.const import UnitOfMeasurement
from pyplumio.parameters.custom import CustomParameters, ParameterOverride, Signature
from pyplumio.parameters.ecomax import EcomaxNumberDescription, EcomaxSwitchDescription


class EcoMAX860D3HB(CustomParameters):
    """Custom parameters for ecoMAX 860D3-HB."""

    signature = Signature(model="ecoMAX 860D3-HB", id=48)

    overrides = (
        # Summer mode
        ParameterOverride(
            original="summer_mode_disable_temp",
            replacement=EcomaxNumberDescription(name="__unknown_parameter_1"),
        ),
        ParameterOverride(
            original="water_heater_target_temp",
            replacement=EcomaxNumberDescription(name="summer_mode"),
        ),
        ParameterOverride(
            original="min_water_heater_target_temp",
            replacement=EcomaxNumberDescription(
                name="summer_mode_enable_temp",
                unit_of_measurement=UnitOfMeasurement.CELSIUS,
            ),
        ),
        ParameterOverride(
            original="max_water_heater_target_temp",
            replacement=EcomaxNumberDescription(
                name="summer_mode_disable_temp",
                unit_of_measurement=UnitOfMeasurement.CELSIUS,
            ),
        ),
        # Water heater
        ParameterOverride(
            original="disable_pump_on_thermostat",
            replacement=EcomaxNumberDescription(
                name="water_heater_target_temp",
                unit_of_measurement=UnitOfMeasurement.CELSIUS,
            ),
        ),
        ParameterOverride(
            original="boiler_alert_temp",
            replacement=EcomaxNumberDescription(
                name="min_water_heater_target_temp",
                unit_of_measurement=UnitOfMeasurement.CELSIUS,
            ),
        ),
        ParameterOverride(
            original="max_feeder_temp",
            replacement=EcomaxNumberDescription(
                name="max_water_heater_target_temp",
                unit_of_measurement=UnitOfMeasurement.CELSIUS,
            ),
        ),
        ParameterOverride(
            original="water_heater_work_mode",
            replacement=EcomaxNumberDescription(name="water_heater_feeding_extension"),
        ),
        ParameterOverride(
            original="external_boiler_temp",
            replacement=EcomaxNumberDescription(name="water_heater_work_mode"),
        ),
        ParameterOverride(
            original="alert_notify",
            replacement=EcomaxNumberDescription(
                name="water_heater_hysteresis",
                unit_of_measurement=UnitOfMeasurement.CELSIUS,
            ),
        ),
        ParameterOverride(
            original="pump_hysteresis",
            replacement=EcomaxSwitchDescription(name="water_heater_disinfection"),
        ),
    )
