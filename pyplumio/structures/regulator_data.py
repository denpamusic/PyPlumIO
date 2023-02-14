"""Contains regulator data structure decoder."""
from __future__ import annotations

from typing import Final

from pyplumio.helpers.data_types import Boolean, DataType
from pyplumio.helpers.event_manager import EventManager
from pyplumio.helpers.typing import EventDataType
from pyplumio.structures import StructureDecoder, ensure_device_data
from pyplumio.structures.data_schema import ATTR_SCHEMA
from pyplumio.structures.frame_versions import FrameVersionsStructure

ATTR_REGDATA: Final = "regdata"
ATTR_REGDATA_DECODER: Final = "regdata_decoder"

REGDATA_VERSION: Final = "1.0"


class RegulatorData(EventManager):
    """Represents regulator data."""


def _unpack_data(
    data_type: DataType, data: bytes, boolean_index: int = 0
) -> tuple[DataType, int]:
    """Unpack data into the data type."""
    data_type.unpack(data)
    if isinstance(data_type, Boolean):
        return data_type, data_type.index(boolean_index)

    return data_type, boolean_index


def _decode_regulator_data(
    message: bytearray,
    offset: int,
    schema: list[tuple[int, DataType]],
    boolean_index: int = 0,
) -> EventDataType:
    """Decode regulator data from the schema."""
    data: EventDataType = {}
    for sensor_id, data_type in schema:
        if not isinstance(data_type, Boolean) and boolean_index > 0:
            offset += 1
            boolean_index = 0

        data_type, boolean_index = _unpack_data(
            data_type, message[offset:], boolean_index
        )
        data[sensor_id] = data_type.value
        offset += data_type.size

    return data


class RegulatorDataStructure(StructureDecoder):
    """Represents regulator data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: EventDataType | None = None
    ) -> tuple[EventDataType, int]:
        """Decode bytes and return message data and offset."""
        data = ensure_device_data(data)
        schema = data.get(ATTR_SCHEMA, [])
        offset += 2
        regdata_version = f"{message[offset+1]}.{message[offset]}"
        if regdata_version != REGDATA_VERSION:
            return data, offset

        data, offset = FrameVersionsStructure(self.frame).decode(
            message, offset + 2, data
        )
        sensors = _decode_regulator_data(message, offset, schema)
        if not sensors:
            return ensure_device_data(data), offset

        data.setdefault(ATTR_REGDATA, RegulatorData()).load(sensors)
        return ensure_device_data(data), offset
