"""Contains product info structure decoder."""

import struct
from typing import Optional, Tuple

from pyplumio import util
from pyplumio.const import ATTR_PRODUCT
from pyplumio.helpers.product_info import ProductInfo
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.helpers.uid import unpack_uid
from pyplumio.structures import StructureDecoder, make_device_data


class ProductInfoStructure(StructureDecoder):
    """Represents product info data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        product_info = ProductInfo()
        product_info.type, product_info.product = struct.unpack_from("<BH", message)
        product_info.uid = unpack_uid(message, offset)
        product_info.logo, product_info.image = struct.unpack_from("<HH", message)
        product_info.model = util.unpack_string(message, offset + 16)

        return make_device_data(data, {ATTR_PRODUCT: product_info}), offset
