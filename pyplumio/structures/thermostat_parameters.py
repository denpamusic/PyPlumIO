"""Contains thermostat parameter structure decoder."""
from __future__ import annotations

from typing import Final, Iterable, List, Optional, Tuple

from pyplumio import util
from pyplumio.helpers.typing import DeviceDataType, ParameterDataType
from pyplumio.structures import StructureDecoder, ensure_device_data
from pyplumio.structures.thermostat_sensors import ATTR_THERMOSTAT_COUNT

ATTR_THERMOSTAT_PROFILE: Final = "thermostat_profile"
ATTR_THERMOSTAT_PARAMETERS: Final = "thermostat_parameters"
ATTR_THERMOSTAT_PARAMETERS_DECODER: Final = "thermostat_parameters_decoder"

THERMOSTAT_PARAMETERS: Tuple[str, ...] = (
    "mode",
    "party_target_temp",
    "summer_target_temp",
    "correction",
    "away_timer",
    "vent_timer",
    "party_timer",
    "holiday_timer",
    "hysteresis",
    "day_target_temp",
    "night_target_temp",
    "antifreeze_target_temp",
    "heating_target_temp",
    "heating_timer",
    "off_timer",
)


def _decode_thermostat_parameters(
    message: bytearray, offset: int, indexes: Iterable
) -> Tuple[List[Tuple[int, ParameterDataType]], int]:
    """Decode parameters for a single thermostat."""
    parameters: List[Tuple[int, ParameterDataType]] = []
    for index in indexes:
        parameter_size = (
            2 if THERMOSTAT_PARAMETERS[index].endswith("target_temp") else 1
        )
        parameter = util.unpack_parameter(message, offset, size=parameter_size)
        if parameter is not None:
            parameters.append((index, parameter))

        offset += 3 * parameter_size

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
            return data, offset

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
            return data, offset

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
