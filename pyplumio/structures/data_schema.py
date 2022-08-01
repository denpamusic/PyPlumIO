"""Contains data schema structure decoder."""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from pyplumio import util
from pyplumio.const import ATTR_MODE, ATTR_SCHEMA
from pyplumio.helpers.data_types import DATA_TYPES, DataType
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures import StructureDecoder, make_device_data
from pyplumio.structures.outputs import (
    FAN_OUTPUT,
    FEEDER_OUTPUT,
    HEATING_PUMP_OUTPUT,
    LIGHTER_OUTPUT,
    WATER_HEATER_PUMP_OUTPUT,
)
from pyplumio.structures.statuses import HEATING_TARGET, WATER_HEATER_TARGET
from pyplumio.structures.temperatures import (
    EXHAUST_TEMP,
    FEEDER_TEMP,
    HEATING_TEMP,
    OUTSIDE_TEMP,
    WATER_HEATER_TEMP,
)

REGDATA_SCHEMA: Dict[int, str] = {
    1792: ATTR_MODE,
    1024: HEATING_TEMP,
    1026: FEEDER_TEMP,
    1025: WATER_HEATER_TEMP,
    1027: OUTSIDE_TEMP,
    1030: EXHAUST_TEMP,
    1280: HEATING_TARGET,
    1281: WATER_HEATER_TARGET,
    1536: FAN_OUTPUT,
    1538: FEEDER_OUTPUT,
    1541: HEATING_PUMP_OUTPUT,
    1542: WATER_HEATER_PUMP_OUTPUT,
    3: LIGHTER_OUTPUT,
}


class DataSchemaStructure(StructureDecoder):
    """Represent data schema structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        blocks_number = util.unpack_ushort(message[offset : offset + 2])
        offset += 2
        schema: List[Tuple[str, DataType]] = []
        if blocks_number > 0:
            for _ in range(blocks_number):
                param_type = message[offset]
                param_id = util.unpack_ushort(message[offset + 1 : offset + 3])
                param_name = REGDATA_SCHEMA.get(param_id, str(param_id))
                schema.append((param_name, DATA_TYPES[param_type]()))
                offset += 3

        return make_device_data(data, {ATTR_SCHEMA: schema}), offset
