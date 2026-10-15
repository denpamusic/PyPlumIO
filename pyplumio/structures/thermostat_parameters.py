"""Contains a thermostat parameters structure decoder."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any, Final, TypeAlias

from pyplumio.parameters import ParameterValues, unpack_parameter
from pyplumio.parameters.thermostat import get_thermostat_parameter_types
from pyplumio.structures import StructureDecoder
from pyplumio.structures.sensor_data import ATTR_THERMOSTATS_AVAILABLE

ATTR_THERMOSTAT_PROFILE: Final = "thermostat_profile"
ATTR_THERMOSTAT_PARAMETERS: Final = "thermostat_parameters"

THERMOSTAT_PARAMETER_SIZE: Final = 3


_ParameterValues: TypeAlias = tuple[int, ParameterValues]


class ThermostatParametersStructure(StructureDecoder):
    """Represents a thermostat parameters data structure."""

    def _thermostat_parameter(
        self, message: bytes, thermostats: int, start: int, end: int
    ) -> Generator[_ParameterValues]:
        """Get a single thermostat parameter."""
        parameter_types = get_thermostat_parameter_types()
        for index in range(start, (start + end) // thermostats):
            description = parameter_types[index]
            if parameter := unpack_parameter(
                message, self._offset, size=description.size
            ):
                yield (index, parameter)

            self._offset += THERMOSTAT_PARAMETER_SIZE * description.size

    def _thermostat_parameters(
        self, message: bytes, thermostats: int, start: int, end: int
    ) -> Generator[tuple[int, list[_ParameterValues]]]:
        """Get parameters for a thermostat."""
        for index in range(thermostats):
            if parameters := list(
                self._thermostat_parameter(message, thermostats, start, end)
            ):
                yield (index, parameters)

    def decode(self, message: bytes, data: dict[str, Any], offset: int = 0) -> None:
        """Decode bytes and return message data and offset."""
        device = self.frame.handler
        if not device or not (
            thermostats := device.get_nowait(ATTR_THERMOSTATS_AVAILABLE, None)
        ):
            data[ATTR_THERMOSTAT_PARAMETERS] = None
            return

        start = message[offset + 1]
        end = message[offset + 2]
        offset += 3
        thermostat_profile = unpack_parameter(message, offset)
        self._offset = offset + THERMOSTAT_PARAMETER_SIZE
        data[ATTR_THERMOSTAT_PROFILE] = thermostat_profile
        data[ATTR_THERMOSTAT_PARAMETERS] = dict(
            self._thermostat_parameters(message, thermostats, start, end)
        )


__all__ = [
    "ATTR_THERMOSTAT_PROFILE",
    "ATTR_THERMOSTAT_PARAMETERS",
    "ThermostatParametersStructure",
]
