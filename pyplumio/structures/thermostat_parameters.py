"""Contains thermostat parameter structure decoder."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Iterable, List, Optional, Tuple, Type

from pyplumio import util
from pyplumio.const import ATTR_INDEX, ATTR_OFFSET, ATTR_VALUE
from pyplumio.devices import Thermostat
from pyplumio.frames import Request
from pyplumio.helpers.factory import factory
from pyplumio.helpers.parameter import BinaryParameter, Parameter, ParameterDescription
from pyplumio.helpers.typing import (
    DeviceDataType,
    ParameterDataType,
    ParameterValueType,
)
from pyplumio.structures import StructureDecoder, ensure_device_data
from pyplumio.structures.thermostat_sensors import ATTR_THERMOSTAT_COUNT

ATTR_THERMOSTAT_PROFILE: Final = "thermostat_profile"
ATTR_THERMOSTAT_PARAMETERS: Final = "thermostat_parameters"
ATTR_THERMOSTAT_PARAMETERS_DECODER: Final = "thermostat_parameters_decoder"


class ThermostatParameter(Parameter):
    """Represents thermostat parameter."""

    device: Thermostat
    description: ThermostatParameterDescription
    offset: int

    def __init__(self, offset: int, *args, **kwargs):
        """Initialize ThermostatParameter object."""
        self.offset = offset
        super().__init__(*args, **kwargs)

    async def set(self, value: ParameterValueType, retries: int = 5) -> bool:
        """Set parameter value."""
        if isinstance(value, (int, float)):
            value *= self.description.multiplier

        return await super().set(value, retries)

    @property
    def value(self) -> ParameterValueType:
        """Return parameter value."""
        return self._value / self.description.multiplier

    @property
    def min_value(self) -> ParameterValueType:
        """Return minimum allowed value."""
        return self._min_value / self.description.multiplier

    @property
    def max_value(self) -> ParameterValueType:
        """Return maximum allowed value."""
        return self._max_value / self.description.multiplier

    @property
    def request(self) -> Request:
        """Return request to change the parameter."""
        return factory(
            "frames.requests.SetThermostatParameterRequest",
            recipient=self.device.parent.address,
            data={
                # Increase the index by one to account for thermostat
                # profile, which is being set at ecoMAX device level.
                ATTR_INDEX: self._index + 1,
                ATTR_VALUE: self._value,
                ATTR_OFFSET: self.offset,
            },
        )


class ThermostatBinaryParameter(BinaryParameter, ThermostatParameter):
    """Represents thermostat binary parameter."""


@dataclass
class ThermostatParameterDescription(ParameterDescription):
    """Represents thermostat parameter description."""

    cls: Type[ThermostatParameter] = ThermostatParameter
    multiplier: int = 1
    size: int = 1


THERMOSTAT_PARAMETERS: Tuple[ThermostatParameterDescription, ...] = (
    ThermostatParameterDescription(name="mode"),
    ThermostatParameterDescription(name="party_target_temp", size=2, multiplier=10),
    ThermostatParameterDescription(name="summer_target_temp", size=2, multiplier=10),
    ThermostatParameterDescription(name="correction"),
    ThermostatParameterDescription(name="away_timer"),
    ThermostatParameterDescription(name="vent_timer"),
    ThermostatParameterDescription(name="party_timer"),
    ThermostatParameterDescription(name="holiday_timer"),
    ThermostatParameterDescription(name="hysteresis", multiplier=10),
    ThermostatParameterDescription(name="day_target_temp", size=2, multiplier=10),
    ThermostatParameterDescription(name="night_target_temp", size=2, multiplier=10),
    ThermostatParameterDescription(
        name="antifreeze_target_temp", size=2, multiplier=10
    ),
    ThermostatParameterDescription(name="heating_target_temp", size=2, multiplier=10),
    ThermostatParameterDescription(name="heating_timer"),
    ThermostatParameterDescription(name="off_timer"),
)


def _decode_thermostat_parameters(
    message: bytearray, offset: int, indexes: Iterable
) -> Tuple[List[Tuple[int, ParameterDataType]], int]:
    """Decode parameters for a single thermostat."""
    parameters: List[Tuple[int, ParameterDataType]] = []
    for index in indexes:
        description = THERMOSTAT_PARAMETERS[index]
        parameter = util.unpack_parameter(message, offset, size=description.size)
        if parameter is not None:
            parameters.append((index, parameter))

        offset += 3 * description.size

    return parameters, offset


class ThermostatParametersStructure(StructureDecoder):
    """Represent thermostat parameters data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        data = ensure_device_data(data)
        thermostat_count = data.get(ATTR_THERMOSTAT_COUNT, 0)
        if thermostat_count == 0:
            return (
                ensure_device_data(
                    data,
                    {ATTR_THERMOSTAT_PARAMETERS: None, ATTR_THERMOSTAT_PROFILE: None},
                ),
                offset,
            )

        first_index = message[offset + 1]
        last_index = message[offset + 2]
        thermostat_profile = util.unpack_parameter(message, offset + 3)
        parameter_count_per_thermostat = (first_index + last_index) // thermostat_count
        offset += 6
        thermostat_parameters: List[
            Tuple[int, List[Tuple[int, ParameterDataType]]]
        ] = []
        for index in range(thermostat_count):
            parameters, offset = _decode_thermostat_parameters(
                message,
                offset,
                range(first_index, parameter_count_per_thermostat),
            )
            if parameters:
                thermostat_parameters.append((index, parameters))

        if not thermostat_parameters:
            # No thermostat parameters detected.
            return (
                ensure_device_data(
                    data,
                    {ATTR_THERMOSTAT_PARAMETERS: None, ATTR_THERMOSTAT_PROFILE: None},
                ),
                offset,
            )

        return (
            ensure_device_data(
                data,
                {
                    ATTR_THERMOSTAT_PROFILE: thermostat_profile,
                    ATTR_THERMOSTAT_PARAMETERS: thermostat_parameters,
                },
            ),
            offset,
        )
