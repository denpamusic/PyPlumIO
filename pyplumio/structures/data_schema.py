"""Contains data schema structure decoder."""
from __future__ import annotations

from typing import Dict, Final, List, Optional, Tuple

from pyplumio import util
from pyplumio.const import ATTR_STATE
from pyplumio.helpers.data_types import DATA_TYPES, DataType
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures import StructureDecoder, ensure_device_data
from pyplumio.structures.outputs import (
    ATTR_FAN,
    ATTR_FEEDER,
    ATTR_HEATING_PUMP,
    ATTR_LIGHTER,
    ATTR_WATER_HEATER_PUMP,
)
from pyplumio.structures.statuses import ATTR_HEATING_TARGET, ATTR_WATER_HEATER_TARGET
from pyplumio.structures.temperatures import (
    ATTR_EXHAUST_TEMP,
    ATTR_FEEDER_TEMP,
    ATTR_HEATING_TEMP,
    ATTR_OUTSIDE_TEMP,
    ATTR_WATER_HEATER_TEMP,
)

ATTR_SCHEMA: Final = "schema"

REGDATA_SCHEMA: Dict[int, str] = {
    3: ATTR_LIGHTER,
    1024: ATTR_HEATING_TEMP,
    1026: ATTR_FEEDER_TEMP,
    1025: ATTR_WATER_HEATER_TEMP,
    1027: ATTR_OUTSIDE_TEMP,
    1030: ATTR_EXHAUST_TEMP,
    1280: ATTR_HEATING_TARGET,
    1281: ATTR_WATER_HEATER_TARGET,
    1536: ATTR_FAN,
    1538: ATTR_FEEDER,
    1541: ATTR_HEATING_PUMP,
    1542: ATTR_WATER_HEATER_PUMP,
    1792: ATTR_STATE,
}


class DataSchemaStructure(StructureDecoder):
    """Represent data schema structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        blocks_count = util.unpack_ushort(message[offset : offset + 2])
        offset += 2
        if blocks_count == 0:
            return ensure_device_data(data), offset

        schema: List[Tuple[str, DataType]] = []
        for _ in range(blocks_count):
            param_type = message[offset]
            param_id = util.unpack_ushort(message[offset + 1 : offset + 3])
            param_name = REGDATA_SCHEMA.get(param_id, str(param_id))
            schema.append((param_name, DATA_TYPES[param_type]()))
            offset += 3

        return ensure_device_data(data, {ATTR_SCHEMA: schema}), offset
