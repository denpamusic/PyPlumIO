from pyplumio import econet_connection
from pyplumio.econet import EcoNET


def test_econet_connection():
    econet = econet_connection("localhost", 8899)
    assert isinstance(econet, EcoNET)
