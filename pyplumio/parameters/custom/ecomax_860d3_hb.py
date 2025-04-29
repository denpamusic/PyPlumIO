"""Contains patch for ecoMAX 860D3-HB."""

from pyplumio.const import UnitOfMeasurement
from pyplumio.parameters.custom import CustomParameter, CustomParameters, Signature
from pyplumio.parameters.ecomax import EcomaxNumberDescription


class EcoMAX860D3HB(CustomParameters):
    """Replacements for ecoMAX 860D3-HB."""

    __slots__ = ()

    signature = Signature(model="ecoMAX 860D3-HB", id=48)

    replacements = (
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
    )
