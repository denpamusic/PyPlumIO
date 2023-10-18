"""Contains a regulator data structure decoder."""
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
    """Represents a regulator data."""


class RegulatorDataStructure(StructureDecoder):
    """Represents a regulator data structure."""

    _offset: int = 0
    _boolean_index: int = 0

    def _unpack_regulator_data(self, message: bytearray, data_type: DataType):
        """Unpack a regulator data sensor."""
        if not isinstance(data_type, Boolean) and self._boolean_index > 0:
            # Current data type is not boolean, but previous was, thus
            # we skip single byte that was left from the boolean
            # and reset boolean index.
            self._offset += 1
            self._boolean_index = 0

        data_type.unpack(message[self._offset :])
        if isinstance(data_type, Boolean):
            self._boolean_index = data_type.next(self._boolean_index)

        try:
            return data_type.value
        finally:
            self._offset += data_type.size

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

        data, self._offset = FrameVersionsStructure(self.frame).decode(
            message, offset + 2, data
        )

        if schema:
            data.setdefault(ATTR_REGDATA, RegulatorData()).load(
                {
                    param_id: self._unpack_regulator_data(message, data_type)
                    for param_id, data_type in schema
                }
            )

        return ensure_device_data(data), self._offset
