"""Contains a product info structure decoder."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache, reduce
import re
import struct
from typing import Any, Final

from pyplumio.const import ProductType
from pyplumio.data_types import UnsignedShort, VarBytes, VarString
from pyplumio.structures import StructureDecoder
from pyplumio.utils import ensure_dict

ATTR_PRODUCT: Final = "product"


CRC: Final = 0xA3A3
POLYNOMIAL: Final = 0xA001
BASE5_KEY: Final = "0123456789ABCDEFGHIJKLMNZPQRSTUV"


def _base5(buffer: bytes) -> str:
    """Encode bytes to a base5 encoded string."""
    number = int.from_bytes(buffer, byteorder="little")
    output = []
    while number:
        output.append(BASE5_KEY[number & 0b00011111])
        number >>= 5

    return "".join(reversed(output))


def _crc16(buffer: bytes) -> bytes:
    """Return a CRC 16."""
    crc16 = reduce(_crc16_byte, buffer, CRC)
    return crc16.to_bytes(length=2, byteorder="little")


def _crc16_byte(crc: int, byte: int) -> int:
    """Add a byte to the CRC."""
    crc ^= byte
    for _ in range(8):
        crc = (crc >> 1) ^ POLYNOMIAL if crc & 1 else crc >> 1

    return crc


def unpack_uid(buffer: bytes) -> str:
    """Unpack UID from bytes."""
    return _base5(buffer + _crc16(buffer))


@cache
def format_model_name(model_name: str) -> str:
    """Format a device model name."""
    if m := re.match(r"^([A-Z]+)\s*(\d{3,})(.+)$", model_name, re.IGNORECASE):
        model_device, model_number, model_suffix = m.groups()
        model_device = "ecoMAX" if model_device == "EM" else model_device
        return f"{model_device} {model_number}{model_suffix}"

    return model_name


@dataclass(frozen=True, slots=True)
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


__all__ = ["ATTR_PRODUCT", "ProductInfo", "ProductInfoStructure"]
