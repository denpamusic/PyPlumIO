"""Contains tests for the UID decoder."""

from pyplumio.helpers.uid import unpack_uid


def test_from_bytes() -> None:
    """Test conversion from bytes."""
    message1 = bytearray.fromhex("0B001600110D383338365539")
    message2 = bytearray.fromhex("0D002500300E191932135831")
    assert unpack_uid(message1) == "D251PAKR3GCPZ1K8G05G0"
    assert unpack_uid(message2) == "CE71HB09J468P1ZZ00980"
