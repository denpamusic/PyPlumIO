"""Test PyPlumIO message frames."""

from pyplumio.constants import BROADCAST_ADDRESS, ECONET_ADDRESS
from pyplumio.frames import messages


def test_responses_type() -> None:
    """Test if response is instance of frame class."""
    for response in (
        messages.RegData,
        messages.CurrentData,
    ):
        frame = response(recipient=BROADCAST_ADDRESS, sender=ECONET_ADDRESS)
        assert isinstance(frame, response)
