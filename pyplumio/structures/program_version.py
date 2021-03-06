"""Contains network program version decoder."""

import struct
from typing import Optional, Tuple

from pyplumio.const import ATTR_VERSION
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.helpers.version_info import VersionInfo
from pyplumio.structures import Structure


class ProgramVersionStructure(Structure):
    """Represents program version data structure."""

    def encode(self, data: DeviceDataType) -> bytearray:
        """Encode device data to bytearray message."""
        message = bytearray(15)
        version_info = data[ATTR_VERSION] if ATTR_VERSION in data else VersionInfo()
        struct.pack_into(
            "<2sB2s3s3HB",
            message,
            0,
            version_info.struct_tag,
            version_info.struct_version,
            version_info.device_id,
            version_info.processor_signature,
            *map(int, version_info.software.split(".", 2)),
            self.frame.sender,
        )
        return message

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        if data is None:
            data = {}

        version_info = VersionInfo()
        [
            version_info.struct_tag,
            version_info.struct_version,
            version_info.device_id,
            version_info.processor_signature,
            software_version1,
            software_version2,
            software_version3,
            self.frame.recipient,
        ] = struct.unpack_from("<2sB2s3s3HB", message)
        version_info.software = ".".join(
            map(str, [software_version1, software_version2, software_version3])
        )
        offset += 15
        data[ATTR_VERSION] = version_info

        return data, offset
