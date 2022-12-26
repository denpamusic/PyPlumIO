"""Contains thermostat parameter structure decoder."""
from __future__ import annotations

from typing import Final, Iterable, List, Optional, Tuple

from pyplumio import util
from pyplumio.const import ATTR_THERMOSTAT_PARAMETERS, ATTR_THERMOSTATS
from pyplumio.helpers.typing import DeviceDataType, ParameterDataType
from pyplumio.structures import StructureDecoder, ensure_device_data

ATTR_THERMOSTAT_PROFILE: Final = "thermostat_profile"

THERMOSTAT_PARAMETERS: Tuple[str, ...] = (
    "thermostat_mode",
    "thermostat_party_target_temp",
    "thermostat_summer_target_temp",
    "thermostat_correction",
    "thermostat_away_timer",
    "thermostat_vent_timer",
    "thermostat_party_timer",
    "thermostat_holiday_timer",
    "thermostat_hysteresis",
    "thermostat_day_target_temp",
    "thermostat_night_target_temp",
    "thermostat_antifreeze_target_temp",
    "thermostat_heating_target_temp",
    "thermostat_heating_timer",
    "thermostat_off_timer",
)


def _decode_thermostat_parameters(
    message: bytearray, offset: int, parameter_name_indexes: Iterable
) -> Tuple[List[Tuple[int, ParameterDataType]], int]:
    """Decode parameters for a single thermostat."""
    thermostat_parameters: List[Tuple[int, ParameterDataType]] = []
    for index in parameter_name_indexes:
        parameter_size = (
            2 if THERMOSTAT_PARAMETERS[index].endswith("target_temp") else 1
        )
        parameter = util.unpack_parameter(message, offset, size=parameter_size)
        if parameter is not None:
            thermostat_parameters.append((index, parameter))

        offset += 3 * parameter_size

    return thermostat_parameters, offset


class ThermostatParametersStructure(StructureDecoder):
    """Represent thermostat parameters data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        data = ensure_device_data(data)
        first_parameter = message[offset + 1]
        parameters_number = message[offset + 2]
        thermostat_numbers = len(data.get(ATTR_THERMOSTATS, []))
        offset += 4
        if thermostat_numbers == 0:
            return ensure_device_data(data), offset

        total_parameters = (parameters_number + first_parameter) // thermostat_numbers
        thermostat_parameters: List[List[Tuple[int, ParameterDataType]]] = []
        thermostat_profile = util.unpack_parameter(message, offset)
        offset += 3
        for _ in range(thermostat_numbers):
            parameters, offset = _decode_thermostat_parameters(
                message,
                offset,
                range(first_parameter, total_parameters),
            )
            if parameters:
                thermostat_parameters.append(parameters)

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
