"""Contains a thermostat parameters structure decoder."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any, Final

from pyplumio.parameters import ParameterValues, unpack_parameter
from pyplumio.parameters.thermostat import get_thermostat_parameter_types
from pyplumio.structures import StructureDecoder
from pyplumio.structures.sensor_data import ATTR_THERMOSTATS_AVAILABLE
from pyplumio.utils import ensure_dict

ATTR_THERMOSTAT_PROFILE: Final = "thermostat_profile"
ATTR_THERMOSTAT_PARAMETERS: Final = "thermostat_parameters"

THERMOSTAT_PARAMETER_SIZE: Final = 3


class ThermostatParametersStructure(StructureDecoder):
    """Represents a thermostat parameters data structure."""

    __slots__ = ("_offset",)

    _offset: int

    def _thermostat_parameter(
        self, message: bytearray, thermostats: int, start: int, end: int
    ) -> Generator[tuple[int, ParameterValues], None, None]:
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
        self, message: bytearray, thermostats: int, start: int, end: int
    ) -> Generator[tuple[int, list[tuple[int, ParameterValues]]], None, None]:
        """Get parameters for a thermostat."""
        for index in range(thermostats):
            if parameters := list(
                self._thermostat_parameter(message, thermostats, start, end)
            ):
                yield (index, parameters)

    def decode(
        self, message: bytearray, offset: int = 0, data: dict[str, Any] | None = None
    ) -> tuple[dict[str, Any], int]:
        """Decode bytes and return message data and offset."""
        device = self.frame.handler
        if not device or not (
            thermostats := device.get_nowait(ATTR_THERMOSTATS_AVAILABLE, None)
        ):
            return ensure_dict(data, {ATTR_THERMOSTAT_PARAMETERS: None}), offset

        start = message[offset + 1]
        end = message[offset + 2]
        offset += 3
        thermostat_profile = unpack_parameter(message, offset)
        self._offset = offset + THERMOSTAT_PARAMETER_SIZE
        return (
            ensure_dict(
                data,
                {
                    ATTR_THERMOSTAT_PROFILE: thermostat_profile,
                    ATTR_THERMOSTAT_PARAMETERS: dict(
                        self._thermostat_parameters(message, thermostats, start, end)
                    ),
                },
            ),
            self._offset,
        )


__all__ = [
    "ATTR_THERMOSTAT_PROFILE",
    "ATTR_THERMOSTAT_PARAMETERS",
    "ThermostatParametersStructure",
]
