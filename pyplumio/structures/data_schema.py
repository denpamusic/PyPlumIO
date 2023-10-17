"""Contains data schema structure decoder."""
from __future__ import annotations

from typing import Final

from pyplumio import util
from pyplumio.helpers.data_types import DATA_TYPES, DataType
from pyplumio.helpers.typing import EventDataType
from pyplumio.structures import StructureDecoder, ensure_device_data

ATTR_SCHEMA: Final = "schema"

BLOCK_SIZE: Final = 3


class DataSchemaStructure(StructureDecoder):
    """Represents a data schema structure."""

    _offset: int

    def _unpack_block(self, message: bytearray) -> tuple[int, DataType]:
        """Unpack a block."""
        param_type = message[self._offset]
        param_id = util.unpack_ushort(
            message[self._offset + 1 : self._offset + BLOCK_SIZE]
        )[0]

        try:
            return param_id, DATA_TYPES[param_type]()
        finally:
            self._offset += BLOCK_SIZE

    def decode(
        self, message: bytearray, offset: int = 0, data: EventDataType | None = None
    ) -> tuple[EventDataType, int]:
        """Decode bytes and return message data and offset."""
        blocks = util.unpack_ushort(message[offset : offset + 2])[0]
        self._offset = offset + 2
        if blocks == 0:
            return ensure_device_data(data), self._offset

        return (
            ensure_device_data(
                data,
                {ATTR_SCHEMA: [self._unpack_block(message) for _ in range(blocks)]},
            ),
            self._offset,
        )
