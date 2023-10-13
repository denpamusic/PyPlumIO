"""Contains data schema structure decoder."""
from __future__ import annotations

from typing import Final

from pyplumio import util
from pyplumio.helpers.data_types import DATA_TYPES, DataType
from pyplumio.helpers.typing import EventDataType
from pyplumio.structures import StructureDecoder, ensure_device_data

ATTR_SCHEMA: Final = "schema"


class DataSchemaStructure(StructureDecoder):
    """Represents a data schema structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: EventDataType | None = None
    ) -> tuple[EventDataType, int]:
        """Decode bytes and return message data and offset."""
        blocks_count = util.unpack_ushort(message[offset : offset + 2])
        offset += 2
        if blocks_count == 0:
            return ensure_device_data(data), offset

        schema: list[tuple[int, DataType]] = []
        for _ in range(blocks_count):
            param_type = message[offset]
            param_id = util.unpack_ushort(message[offset + 1 : offset + 3])
            schema.append((param_id, DATA_TYPES[param_type]()))
            offset += 3

        return ensure_device_data(data, {ATTR_SCHEMA: schema}), offset
