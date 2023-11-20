"""Contains a regulator data structure decoder."""
from __future__ import annotations

from typing import Final

from pyplumio.devices import AddressableDevice
from pyplumio.helpers.data_types import BitArray, DataType
from pyplumio.helpers.event_manager import EventManager
from pyplumio.helpers.typing import EventDataType
from pyplumio.structures import StructureDecoder
from pyplumio.structures.frame_versions import FrameVersionsStructure
from pyplumio.structures.regulator_data_schema import ATTR_REGDATA_SCHEMA
from pyplumio.utils import ensure_dict

ATTR_REGDATA: Final = "regdata"

REGDATA_VERSION: Final = "1.0"


class RegulatorData(EventManager):
    """Represents a regulator data."""


class RegulatorDataStructure(StructureDecoder):
    """Represents a regulator data structure."""

    _offset: int = 0
    _bitarray_index: int = 0

    def _unpack_regulator_data(self, message: bytearray, data_type: DataType):
        """Unpack a regulator data sensor."""
        if not isinstance(data_type, BitArray) and self._bitarray_index > 0:
            # Current data type is not bitarray, but previous was, thus
            # we skip a single byte that was left from the bitarray
            # and reset bitarray index.
            self._offset += 1
            self._bitarray_index = 0

        data_type.unpack(message[self._offset :])
        if isinstance(data_type, BitArray):
            self._bitarray_index = data_type.next(self._bitarray_index)

        try:
            return data_type.value
        finally:
            self._offset += data_type.size

    def decode(
        self, message: bytearray, offset: int = 0, data: EventDataType | None = None
    ) -> tuple[EventDataType, int]:
        """Decode bytes and return message data and offset."""
        data = ensure_dict(data)
        offset += 2
        regdata_version = f"{message[offset+1]}.{message[offset]}"
        if regdata_version != REGDATA_VERSION:
            return data, offset

        data, self._offset = FrameVersionsStructure(self.frame).decode(
            message, offset + 2, data
        )

        sender = self.frame.sender
        if isinstance(sender, AddressableDevice) and (
            schema := sender.get_nowait(ATTR_REGDATA_SCHEMA, [])
        ):
            data.setdefault(ATTR_REGDATA, RegulatorData()).load(
                {
                    param_id: self._unpack_regulator_data(message, data_type)
                    for param_id, data_type in schema
                }
            )

        return data, self._offset
