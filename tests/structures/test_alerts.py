"""Contains tests for alerts structure decoder."""

import datetime as dt

import pytest

from pyplumio.const import AlertType
from pyplumio.frames.responses import AlertsResponse
from pyplumio.structures.alerts import (
    ATTR_ALERTS,
    ATTR_TOTAL_ALERTS,
    Alert,
    AlertsStructure,
    seconds_to_datetime,
)


@pytest.mark.parametrize(
    ("timestamp", "expected_datetime"),
    [
        (946684800, dt.datetime(2029, 6, 15, 0, 0, 0)),
        (1609459200, dt.datetime(2050, 1, 29, 0, 0)),
        (1704067200, dt.datetime(2053, 1, 8, 0, 0)),
        (1735689600, dt.datetime(2054, 1, 2, 0, 0)),
        (2147483647, dt.datetime(2066, 10, 25, 3, 14, 7)),
    ],
)
def test_seconds_to_datetime(timestamp: int, expected_datetime: dt.datetime) -> None:
    """Test conversion of seconds to datetime."""
    dt = seconds_to_datetime(timestamp)
    assert dt == expected_datetime


@pytest.fixture(name="alerts_structure")
def fixture_alerts_structure() -> AlertsStructure:
    """Fixture for AlertsStructure."""
    return AlertsStructure(frame=AlertsResponse())


class TestAlertStructure:
    """Test the Alert structure decoder."""

    def test_decode(self, alerts_structure: AlertsStructure) -> None:
        """Test decoding of alerts structure."""
        message = bytearray(
            [0x01, 0x00, 0x01, 0x00, 0xFF, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01]
        )
        data, offset = alerts_structure.decode(message)
        assert data == {
            ATTR_ALERTS: [
                Alert(
                    code=AlertType.POWER_LOSS,
                    from_dt=dt.datetime(2000, 7, 9, 22, 41, 3),
                    to_dt=dt.datetime(2000, 7, 9, 22, 36, 49),
                )
            ],
            ATTR_TOTAL_ALERTS: 1,
        }
        assert offset == 12

    def test_decode_without_alerts(self, alerts_structure: AlertsStructure) -> None:
        """Test decoding of alerts structure without any alerts."""
        message = bytearray([0x00, 0x00, 0x00])
        data, offset = alerts_structure.decode(message)
        assert data == {ATTR_TOTAL_ALERTS: 0}
        assert offset == 3
