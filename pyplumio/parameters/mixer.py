"""Contains mixer parameter descriptors."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from typing import TYPE_CHECKING

from dataslots import dataslots

from pyplumio.const import (
    ATTR_DEVICE_INDEX,
    ATTR_INDEX,
    ATTR_VALUE,
    FrameType,
    ProductType,
    UnitOfMeasurement,
)
from pyplumio.frames import Request
from pyplumio.parameters import (
    OffsetNumber,
    OffsetNumberDescription,
    Parameter,
    ParameterDescription,
    Switch,
    SwitchDescription,
)
from pyplumio.structures.product_info import ProductInfo

if TYPE_CHECKING:
    from pyplumio.devices.mixer import Mixer


@dataclass
class MixerParameterDescription(ParameterDescription):
    """Represents a mixer parameter description."""

    __slots__ = ()


class MixerParameter(Parameter):
    """Represent a mixer parameter."""

    __slots__ = ()

    device: Mixer
    description: MixerParameterDescription

    async def create_request(self) -> Request:
        """Create a request to change the parameter."""
        return await Request.create(
            FrameType.REQUEST_SET_MIXER_PARAMETER,
            recipient=self.device.parent.address,
            data={
                ATTR_INDEX: self._index,
                ATTR_VALUE: self.values.value,
                ATTR_DEVICE_INDEX: self.device.index,
            },
        )


@dataclass
class MixerNumberDescription(MixerParameterDescription, OffsetNumberDescription):
    """Represent a mixer number description."""

    __slots__ = ()


class MixerNumber(MixerParameter, OffsetNumber):
    """Represents a mixer number."""

    __slots__ = ()

    description: MixerNumberDescription


@dataslots
@dataclass
class MixerSwitchDescription(MixerParameterDescription, SwitchDescription):
    """Represents a mixer switch description."""


class MixerSwitch(MixerParameter, Switch):
    """Represents a mixer switch."""

    __slots__ = ()

    description: MixerSwitchDescription


PARAMETER_TYPES: dict[ProductType, list[MixerParameterDescription]] = {
    ProductType.ECOMAX_P: [
        MixerNumberDescription(
            name="mixer_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        MixerNumberDescription(
            name="min_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        MixerNumberDescription(
            name="max_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        MixerNumberDescription(
            name="thermostat_decrease_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        MixerSwitchDescription(
            name="weather_control",
        ),
        MixerNumberDescription(
            name="heating_curve",
            step=0.1,
        ),
        MixerNumberDescription(
            name="heating_curve_shift",
            offset=20,
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        MixerNumberDescription(
            name="weather_factor",
        ),
        MixerNumberDescription(
            name="work_mode",
        ),
        MixerNumberDescription(
            name="mixer_input_dead_zone",
            step=0.1,
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        MixerSwitchDescription(
            name="thermostat_operation",
        ),
        MixerNumberDescription(
            name="thermostat_mode",
        ),
        MixerSwitchDescription(
            name="disable_pump_on_thermostat",
        ),
        MixerSwitchDescription(
            name="summer_work",
        ),
    ],
    ProductType.ECOMAX_I: [
        MixerNumberDescription(
            name="work_mode",
        ),
        MixerNumberDescription(
            name="circuit_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        MixerNumberDescription(
            name="day_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        MixerNumberDescription(
            name="night_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        MixerNumberDescription(
            name="min_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        MixerNumberDescription(
            name="max_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        MixerSwitchDescription(
            name="summer_work",
        ),
        MixerSwitchDescription(
            name="weather_control",
        ),
        MixerNumberDescription(
            name="enable_circuit",
        ),
        MixerNumberDescription(
            name="constant_water_preset_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        MixerNumberDescription(
            name="thermostat_decrease_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        MixerNumberDescription(
            name="thermostat_correction",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        MixerSwitchDescription(
            name="thermostat_pump_lock",
        ),
        MixerNumberDescription(
            name="valve_opening_time",
            unit_of_measurement=UnitOfMeasurement.SECONDS,
        ),
        MixerNumberDescription(
            name="mixer_input_dead_zone",
            step=0.1,
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        MixerNumberDescription(
            name="proportional_range",
        ),
        MixerNumberDescription(
            name="integration_time_constant",
        ),
        MixerNumberDescription(
            name="heating_curve",
            step=0.1,
        ),
        MixerNumberDescription(
            name="heating_curve_shift",
            offset=20,
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        MixerNumberDescription(
            name="thermostat_mode",
        ),
        MixerNumberDescription(
            name="decreasing_constant_water_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
    ],
}


@cache
def get_mixer_parameter_types(
    product_info: ProductInfo,
) -> list[MixerParameterDescription]:
    """Return cached mixer parameter types for specific product."""
    return PARAMETER_TYPES[product_info.type]


__all__ = [
    "get_mixer_parameter_types",
    "MixerNumber",
    "MixerNumberDescription",
    "MixerParameter",
    "MixerParameterDescription",
    "MixerSwitch",
    "MixerSwitchDescription",
    "PARAMETER_TYPES",
]
