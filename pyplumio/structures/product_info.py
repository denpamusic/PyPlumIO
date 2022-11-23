"""Contains product info structure decoder."""

import struct
from typing import Optional, Tuple

from pyplumio import util
from pyplumio.const import ATTR_PRODUCT
from pyplumio.helpers.product_info import ProductInfo, ProductTypes
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.helpers.uid import unpack_uid
from pyplumio.structures import StructureDecoder, make_device_data


class ProductInfoStructure(StructureDecoder):
    """Represents product info data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        product_type, product_name = struct.unpack_from("<BH", message)
        product_uid = unpack_uid(message, offset)
        product_logo, product_image = struct.unpack_from("<HH", message)
        product_model = util.unpack_string(message, offset + 16)

        return (
            make_device_data(
                data,
                {
                    ATTR_PRODUCT: ProductInfo(
                        type=ProductTypes(product_type),
                        product=product_name,
                        uid=product_uid,
                        logo=product_logo,
                        image=product_image,
                        model=product_model,
                    )
                },
            ),
            offset,
        )
