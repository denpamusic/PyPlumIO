"""Contains regulator data structure decoder."""
from __future__ import annotations

from typing import Final, List, Optional, Tuple

from pyplumio.helpers.data_types import Boolean, DataType
from pyplumio.helpers.typing import BytesType, DeviceDataType
from pyplumio.structures import StructureDecoder, ensure_device_data
from pyplumio.structures.data_schema import ATTR_SCHEMA
from pyplumio.structures.frame_versions import FrameVersionsStructure

ATTR_REGDATA: Final = "regdata"
ATTR_REGDATA_DECODER: Final = "regdata_decoder"

REGDATA_VERSION: Final = "1.0"


def _unpack_data(
    data_type: DataType, data: BytesType, boolean_index: int = 0
) -> Tuple[DataType, int]:
    """Unpack data into the data type."""
    data_type.unpack(data)
    if isinstance(data_type, Boolean):
        return data_type, data_type.index(boolean_index)

    return data_type, boolean_index


def _decode_regulator_data(
    message: bytearray,
    offset: int,
    schema: List[Tuple[str, DataType]],
    boolean_index: int = 0,
) -> DeviceDataType:
    """Decode regulator data from the schema."""
    data = ensure_device_data(None)
    for (sensor_id, data_type) in schema:
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
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
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

        return ensure_device_data(data, {ATTR_REGDATA: sensors}), offset
