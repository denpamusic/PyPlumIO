"""Contains regulator data structure decoder."""
from __future__ import annotations

from typing import Final, List, Optional, Tuple

from pyplumio.const import ATTR_REGDATA, ATTR_SCHEMA, ATTR_STATE, DeviceState
from pyplumio.helpers.data_types import Boolean, DataType
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures import StructureDecoder, make_device_data
from pyplumio.structures.frame_versions import FrameVersionsStructure

REGDATA_VERSION: Final = "1.0"


def _decode_regulator_data(
    message: bytearray, offset: int, schema: List[Tuple[str, DataType]]
) -> DeviceDataType:
    """Decode regulator data from the schema."""
    regulator_data: DeviceDataType = {}
    boolean_index = 0
    for parameter in schema:
        parameter_id, parameter_type = parameter

        if not isinstance(parameter_type, Boolean) and boolean_index > 0:
            offset += 1
            boolean_index = 0

        parameter_type.unpack(message[offset:])
        if isinstance(parameter_type, Boolean):
            boolean_index = parameter_type.index(boolean_index)

        regulator_data[parameter_id] = parameter_type.value

        offset += parameter_type.size

    return regulator_data


class RegulatorDataStructure(StructureDecoder):
    """Represents regulator data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        data = make_device_data(data)
        schema = data.get(ATTR_SCHEMA, [])
        offset += 2
        frame_version = f"{message[offset+1]}.{message[offset]}"
        if frame_version != REGDATA_VERSION:
            return data, offset

        data, offset = FrameVersionsStructure(self.frame).decode(
            message, offset + 2, data
        )
        regulator_data = _decode_regulator_data(message, offset, schema)
        if not regulator_data:
            return make_device_data(data), offset

        try:
            regulator_data[ATTR_STATE] = DeviceState(regulator_data[ATTR_STATE])
        except (ValueError, KeyError):
            pass

        return make_device_data(data, {ATTR_REGDATA: regulator_data}), offset
