"""Contains thermostat parameter structure decoder."""
from __future__ import annotations

from typing import Final, Iterable, List, Optional, Tuple

from pyplumio import util
from pyplumio.const import ATTR_THERMOSTAT_PARAMETERS, ATTR_THERMOSTATS_NUMBER
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
        thermostats_number = data.get(ATTR_THERMOSTATS_NUMBER, 0)
        if thermostats_number == 0:
            return data, offset

        first_parameter = message[offset + 1]
        parameters_number = message[offset + 2]
        offset += 3
        total_parameters_per_thermostat = (
            parameters_number + first_parameter
        ) // thermostats_number
        thermostat_profile = util.unpack_parameter(message, offset)
        offset += 3
        thermostat_parameters: List[
            Tuple[int, List[Tuple[int, ParameterDataType]]]
        ] = []
        for thermostat_number in range(thermostats_number):
            parameters, offset = _decode_thermostat_parameters(
                message,
                offset,
                range(first_parameter, total_parameters_per_thermostat),
            )
            if parameters:
                thermostat_parameters.append((thermostat_number, parameters))

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
