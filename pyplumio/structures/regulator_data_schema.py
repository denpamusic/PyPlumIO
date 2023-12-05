"""Contains data schema structure decoder."""
from __future__ import annotations

from typing import Any, Final

from pyplumio.helpers.data_types import DATA_TYPES, DataType, UnsignedShort
from pyplumio.structures import StructureDecoder
from pyplumio.utils import ensure_dict

ATTR_REGDATA_SCHEMA: Final = "regdata_schema"


class RegulatorDataSchemaStructure(StructureDecoder):
    """Represents a regulator data schema structure."""

    __slots__ = ("_offset",)

    _offset: int

    def _unpack_block(self, message: bytearray) -> tuple[int, DataType]:
        """Unpack a block."""
        param_type = message[self._offset]
        self._offset += 1
        param_id = UnsignedShort.from_bytes(message, self._offset)
        self._offset += param_id.size
        return param_id.value, DATA_TYPES[param_type]()

    def decode(
        self, message: bytearray, offset: int = 0, data: dict[str, Any] | None = None
    ) -> tuple[dict[str, Any], int]:
        """Decode bytes and return message data and offset."""
        blocks = UnsignedShort.from_bytes(message, offset)
        self._offset = offset + blocks.size
        if blocks.value == 0:
            return ensure_dict(data), self._offset

        return (
            ensure_dict(
                data,
                {
                    ATTR_REGDATA_SCHEMA: [
                        self._unpack_block(message) for _ in range(blocks.value)
                    ]
                },
            ),
            self._offset,
        )
