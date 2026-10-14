"""Contains data schema structure decoder."""

from __future__ import annotations

from typing import Any, Final

from pyplumio.data_types import DATA_TYPES, DataType, UnsignedShort
from pyplumio.structures import StructureDecoder

ATTR_REGDATA_SCHEMA: Final = "regdata_schema"


class RegulatorDataSchemaStructure(StructureDecoder):
    """Represents a regulator data schema structure."""

    def _unpack_block(self, message: bytearray) -> tuple[int, DataType]:
        """Unpack a block."""
        param_type = message[self._offset]
        param_id = UnsignedShort.from_bytes(message, self._offset + 1)
        self._offset += param_id.size + 1
        return param_id.value, DATA_TYPES[param_type]()

    def decode(self, message: bytearray, data: dict[str, Any], offset: int = 0) -> None:
        """Decode bytes and return message data and offset."""
        blocks = UnsignedShort.from_bytes(message, offset)
        self._offset = offset + blocks.size
        if blocks.value > 0:
            data[ATTR_REGDATA_SCHEMA] = [
                self._unpack_block(message) for _ in range(blocks.value)
            ]


__all__ = ["ATTR_REGDATA_SCHEMA", "RegulatorDataSchemaStructure"]
