"""Contains a product info structure decoder."""
from __future__ import annotations

from dataclasses import dataclass
import struct
from typing import Final

from pyplumio.const import ProductType
from pyplumio.helpers.data_types import unpack_string
from pyplumio.helpers.typing import EventDataType
from pyplumio.helpers.uid import unpack_uid
from pyplumio.structures import StructureDecoder, ensure_device_data

ATTR_PRODUCT: Final = "product"


@dataclass
class ProductInfo:
    """Represents a product info provided by an UID response."""

    type: ProductType
    id: int
    uid: str
    logo: int
    image: int
    model: str


class ProductInfoStructure(StructureDecoder):
    """Represents a product info data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: EventDataType | None = None
    ) -> tuple[EventDataType, int]:
        """Decode bytes and return message data and offset."""
        product_type, product_id = struct.unpack_from("<BH", message)
        logo, image = struct.unpack_from("<HH", message)
        return (
            ensure_device_data(
                data,
                {
                    ATTR_PRODUCT: ProductInfo(
                        type=ProductType(product_type),
                        id=product_id,
                        uid=unpack_uid(message, offset),
                        logo=logo,
                        image=image,
                        model=unpack_string(message, offset + 16),
                    )
                },
            ),
            offset,
        )
