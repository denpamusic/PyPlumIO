"""Contains a mixer parameter structure decoder."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any, Final, TypeAlias

from pyplumio.parameters import ParameterValues, unpack_parameter
from pyplumio.structures import StructureDecoder

ATTR_MIXER_PARAMETERS: Final = "mixer_parameters"

MIXER_PARAMETER_SIZE: Final = 3

_ParameterValues: TypeAlias = tuple[int, ParameterValues]


class MixerParametersStructure(StructureDecoder):
    """Represents a mixer parameters data structure."""

    def _mixer_parameter(
        self, message: bytes, start: int, end: int
    ) -> Generator[_ParameterValues]:
        """Get a single mixer parameter."""
        for index in range(start, start + end):
            if parameter := unpack_parameter(message, self._offset):
                yield (index, parameter)

            self._offset += MIXER_PARAMETER_SIZE

    def _mixer_parameters(
        self, message: bytes, mixers: int, start: int, end: int
    ) -> Generator[tuple[int, list[_ParameterValues]]]:
        """Get parameters for a mixer."""
        for index in range(mixers):
            if parameters := list(self._mixer_parameter(message, start, end)):
                yield (index, parameters)

    def decode(self, message: bytes, data: dict[str, Any], offset: int = 0) -> None:
        """Decode message into data."""
        start = message[offset + 1]
        end = message[offset + 2]
        mixers = message[offset + 3]
        self._offset = offset + 4
        data[ATTR_MIXER_PARAMETERS] = dict(
            self._mixer_parameters(message, mixers, start, end)
        )


__all__ = [
    "ATTR_MIXER_PARAMETERS",
    "MixerParametersStructure",
]
