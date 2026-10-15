"""Contains regulator parameter structure decoder."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any, Final

from pyplumio.parameters import ParameterValues, unpack_parameter
from pyplumio.structures import StructureDecoder

ATTR_ECOMAX_PARAMETERS: Final = "ecomax_parameters"
ATTR_ECOMAX_CONTROL: Final = "ecomax_control"

ECOMAX_PARAMETER_SIZE: Final = 3


class EcomaxParametersStructure(StructureDecoder):
    """Represents an ecoMAX parameters structure."""

    def _ecomax_parameter(
        self, message: bytes, start: int, end: int
    ) -> Generator[tuple[int, ParameterValues]]:
        """Unpack an ecoMAX parameter."""
        for index in range(start, start + end):
            if parameter := unpack_parameter(message, self._offset):
                yield (index, parameter)

            self._offset += ECOMAX_PARAMETER_SIZE

    def decode(self, message: bytes, data: dict[str, Any], offset: int = 0) -> None:
        """Decode bytes and return message data and offset."""
        start = message[offset + 1]
        end = message[offset + 2]
        self._offset = offset + 3
        data[ATTR_ECOMAX_PARAMETERS] = list(self._ecomax_parameter(message, start, end))


__all__ = ["ATTR_ECOMAX_PARAMETERS", "EcomaxParametersStructure"]
