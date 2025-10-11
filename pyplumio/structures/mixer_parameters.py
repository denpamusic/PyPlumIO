"""Contains a mixer parameter structure decoder."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any, Final, TypeAlias

from pyplumio.parameters import ParameterValues, unpack_parameter
from pyplumio.structures import StructureDecoder
from pyplumio.utils import ensure_dict

ATTR_MIXER_PARAMETERS: Final = "mixer_parameters"

MIXER_PARAMETER_SIZE: Final = 3

_ParameterValues: TypeAlias = tuple[int, ParameterValues]


class MixerParametersStructure(StructureDecoder):
    """Represents a mixer parameters data structure."""

    __slots__ = ("_offset",)

    _offset: int

    def _mixer_parameter(
        self, message: bytearray, start: int, end: int
    ) -> Generator[_ParameterValues]:
        """Get a single mixer parameter."""
        for index in range(start, start + end):
            if parameter := unpack_parameter(message, self._offset):
                yield (index, parameter)

            self._offset += MIXER_PARAMETER_SIZE

    def _mixer_parameters(
        self, message: bytearray, mixers: int, start: int, end: int
    ) -> Generator[tuple[int, list[_ParameterValues]]]:
        """Get parameters for a mixer."""
        for index in range(mixers):
            if parameters := list(self._mixer_parameter(message, start, end)):
                yield (index, parameters)

    def decode(
        self, message: bytearray, offset: int = 0, data: dict[str, Any] | None = None
    ) -> tuple[dict[str, Any], int]:
        """Decode bytes and return message data and offset."""
        start = message[offset + 1]
        end = message[offset + 2]
        mixers = message[offset + 3]
        self._offset = offset + 4
        return (
            ensure_dict(
                data,
                {
                    ATTR_MIXER_PARAMETERS: dict(
                        self._mixer_parameters(message, mixers, start, end)
                    )
                },
            ),
            self._offset,
        )


__all__ = [
    "ATTR_MIXER_PARAMETERS",
    "MixerParametersStructure",
]
