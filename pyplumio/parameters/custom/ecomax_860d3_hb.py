"""Contains patch for ecoMAX 860D3-HB."""

from pyplumio.const import UnitOfMeasurement
from pyplumio.parameters.custom import CustomParameter, CustomParameters, Signature
from pyplumio.parameters.ecomax import EcomaxNumberDescription, EcomaxSwitchDescription


class EcoMAX860D3HB(CustomParameters):
    """Replacements for ecoMAX 860D3-HB."""

    __slots__ = ()

    signature = Signature(model="ecoMAX 860D3-HB", id=48)

    replacements = (
        # Summer mode
        CustomParameter(
            original="summer_mode_disable_temp",
            replacement=EcomaxNumberDescription(name="__unknown_parameter_1"),
        ),
        CustomParameter(
            original="water_heater_target_temp",
            replacement=EcomaxNumberDescription(name="summer_mode"),
        ),
        CustomParameter(
            original="min_water_heater_target_temp",
            replacement=EcomaxNumberDescription(
                name="summer_mode_enable_temp",
                unit_of_measurement=UnitOfMeasurement.CELSIUS,
            ),
        ),
        CustomParameter(
            original="max_water_heater_target_temp",
            replacement=EcomaxNumberDescription(
                name="summer_mode_disable_temp",
                unit_of_measurement=UnitOfMeasurement.CELSIUS,
            ),
        ),
        # Water heater
        CustomParameter(
            original="disable_pump_on_thermostat",
            replacement=EcomaxNumberDescription(
                name="water_heater_target_temp",
                unit_of_measurement=UnitOfMeasurement.CELSIUS,
            ),
        ),
        CustomParameter(
            original="boiler_alert_temp",
            replacement=EcomaxNumberDescription(
                name="min_water_heater_target_temp",
                unit_of_measurement=UnitOfMeasurement.CELSIUS,
            ),
        ),
        CustomParameter(
            original="max_feeder_temp",
            replacement=EcomaxNumberDescription(
                name="max_water_heater_target_temp",
                unit_of_measurement=UnitOfMeasurement.CELSIUS,
            ),
        ),
        CustomParameter(
            original="water_heater_work_mode",
            replacement=EcomaxNumberDescription(name="water_heater_feeding_extension"),
        ),
        CustomParameter(
            original="external_boiler_temp",
            replacement=EcomaxNumberDescription(name="water_heater_work_mode"),
        ),
        CustomParameter(
            original="alert_notify",
            replacement=EcomaxNumberDescription(
                name="water_heater_hysteresis",
                unit_of_measurement=UnitOfMeasurement.CELSIUS,
            ),
        ),
        CustomParameter(
            original="pump_hysteresis",
            replacement=EcomaxSwitchDescription(name="water_heater_disinfection"),
        ),
    )
