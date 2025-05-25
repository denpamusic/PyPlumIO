"""Contains tests for the product info structure decoder."""

import pytest

from pyplumio.structures.product_info import format_model_name, unpack_uid


@pytest.mark.parametrize(
    ("message", "uid"),
    [
        (bytearray.fromhex("001600110D383338365539"), "D251PAKR3GCPZ1K8G05G0"),
        (bytearray.fromhex("002500300E191932135831"), "CE71HB09J468P1ZZ00980"),
    ],
)
def test_from_bytes(message: bytearray, uid: str) -> None:
    """Test unpacking an UID from bytes."""
    assert unpack_uid(message) == uid


@pytest.mark.parametrize(
    ("model_name", "formatted_name"),
    [
        ("EM360P2-ZF", "ecoMAX 360P2-ZF"),
        ("ecoMAXX800R3", "ecoMAXX 800R3"),
        ("ecoMAX850P2-C", "ecoMAX 850P2-C"),
        ("ecoMAX 850i", "ecoMAX 850i"),
        ("ecoMAX 860D3-HB", "ecoMAX 860D3-HB"),
        ("UNKNOWN", "UNKNOWN"),
    ],
)
def test_format_model_name(model_name: str, formatted_name: str) -> None:
    """Test formatting of model names."""
    assert format_model_name(model_name) == formatted_name
