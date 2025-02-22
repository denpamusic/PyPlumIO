"""Contains tests for the UID helper class."""

import pytest

from pyplumio.helpers.uid import unpack_uid


@pytest.mark.parametrize(
    ("message", "uid"),
    [
        ("001600110D383338365539", "D251PAKR3GCPZ1K8G05G0"),
        ("002500300E191932135831", "CE71HB09J468P1ZZ00980"),
    ],
)
def test_from_bytes(message, uid) -> None:
    """Test unpacking an UID from bytes."""
    assert unpack_uid(bytes.fromhex(message)) == uid
