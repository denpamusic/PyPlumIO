"""Contains a product info structure decoder."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
import re
import struct
from typing import Any, Final

from pyplumio.const import ProductType
from pyplumio.helpers.data_types import UnsignedShort, VarBytes, VarString
from pyplumio.helpers.uid import unpack_uid
from pyplumio.structures import StructureDecoder
from pyplumio.utils import ensure_dict

ATTR_PRODUCT: Final = "product"


@cache
def format_model_name(model_name: str) -> str:
    """Format a device model name."""
    if m := re.match(r"^([A-Z]+)\s{0,}([0-9]{3,})(.+)$", model_name, re.IGNORECASE):
        model_device, model_number, model_suffix = m.groups()
        model_device = "ecoMAX" if model_device == "EM" else model_device
        return f"{model_device} {model_number}{model_suffix}"

    return model_name


@dataclass
class ProductInfo:
    """Represents a product info provided by an UID response."""

    __slots__ = ("type", "id", "uid", "logo", "image", "model")

    type: ProductType
    id: int
    uid: str
    logo: int
    image: int
    model: str


class ProductInfoStructure(StructureDecoder):
    """Represents a product info data structure."""

    __slots__ = ()

    def decode(
        self, message: bytearray, offset: int = 0, data: dict[str, Any] | None = None
    ) -> tuple[dict[str, Any], int]:
        """Decode bytes and return message data and offset."""
        product_type, product_id = struct.unpack_from("<BH", message)
        offset += 3
        uid = VarBytes.from_bytes(message, offset)
        offset += uid.size
        logo = UnsignedShort.from_bytes(message, offset)
        offset += logo.size
        image = UnsignedShort.from_bytes(message, offset)
        offset += image.size
        model_name = VarString.from_bytes(message, offset)
        offset += model_name.size

        return (
            ensure_dict(
                data,
                {
                    ATTR_PRODUCT: ProductInfo(
                        type=ProductType(product_type),
                        id=product_id,
                        uid=unpack_uid(uid.value),
                        logo=logo.value,
                        image=image.value,
                        model=format_model_name(model_name.value),
                    )
                },
            ),
            offset,
        )
