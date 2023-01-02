"""Contains product info structure decoder."""

import struct
from typing import Final, Optional, Tuple

from pyplumio import util
from pyplumio.helpers.product_info import ProductInfo, ProductType
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.helpers.uid import unpack_uid
from pyplumio.structures import StructureDecoder, ensure_device_data

ATTR_PRODUCT: Final = "product"


class ProductInfoStructure(StructureDecoder):
    """Represents product info data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        product_type, name = struct.unpack_from("<BH", message)
        uid = unpack_uid(message, offset)
        logo, image = struct.unpack_from("<HH", message)
        model = util.unpack_string(message, offset + 16)

        return (
            ensure_device_data(
                data,
                {
                    ATTR_PRODUCT: ProductInfo(
                        type=ProductType(product_type),
                        product=name,
                        uid=uid,
                        logo=logo,
                        image=image,
                        model=model,
                    )
                },
            ),
            offset,
        )
