"""Contains product info structure decoder."""
from __future__ import annotations

from dataclasses import dataclass
import struct
from typing import Final

from pyplumio import util
from pyplumio.const import ProductType
from pyplumio.helpers.typing import EventDataType
from pyplumio.helpers.uid import unpack_uid
from pyplumio.structures import StructureDecoder, ensure_device_data

ATTR_PRODUCT: Final = "product"


@dataclass
class ProductInfo:
    """Represents product info provided by UID response."""

    type: int
    product: int
    uid: str
    logo: int
    image: int
    model: str


class ProductInfoStructure(StructureDecoder):
    """Represents product info data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: EventDataType | None = None
    ) -> tuple[EventDataType, int]:
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
