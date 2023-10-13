"""Contains an alerts structure decoder."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final

from pyplumio import util
from pyplumio.const import AlertType
from pyplumio.helpers.typing import EventDataType
from pyplumio.structures import StructureDecoder, ensure_device_data

ATTR_ALERTS: Final = "alerts"
ATTR_YEAR: Final = "year"
ATTR_MONTH: Final = "month"
ATTR_DAY: Final = "day"
ATTR_HOUR: Final = "hour"
ATTR_MINUTE: Final = "minute"
ATTR_SECOND: Final = "second"

ALERT_SIZE: Final = 9


def _convert_to_datetime(seconds: int) -> datetime:
    """Convert timestamp to a datetime object."""
    intervals: tuple[tuple[str, int], ...] = (
        (ATTR_YEAR, 32140800),  # 60sec * 60min * 24h * 31d * 12m
        (ATTR_MONTH, 2678400),  # 60sec * 60min * 24h * 31d
        (ATTR_DAY, 86400),  # 60sec * 60min * 24h
        (ATTR_HOUR, 3600),  # 60sec * 60min
        (ATTR_MINUTE, 60),
        (ATTR_SECOND, 1),
    )

    result: dict[str, int] = {}

    for name, count in intervals:
        value = seconds // count
        seconds -= value * count
        result[name] = value

    return datetime(
        year=(result[ATTR_YEAR] + 2000),
        month=(result[ATTR_MONTH] + 1),
        day=(result[ATTR_DAY] + 1),
        hour=result[ATTR_HOUR],
        minute=result[ATTR_MINUTE],
        second=result[ATTR_SECOND],
    )


@dataclass
class Alert:
    """Represents a device alert."""

    code: int
    from_dt: datetime
    to_dt: datetime | None


class AlertsStructure(StructureDecoder):
    """Represents an alerts data structure."""

    _offset: int = 0

    def _unpack_alert(self, message: bytearray) -> Alert:
        """Unpack an alert."""
        try:
            code = message[self._offset]
            code = AlertType(code)
        except ValueError:
            pass

        from_dt = _convert_to_datetime(
            util.unpack_uint(message[self._offset + 1 : self._offset + 5])[0]
        )
        to_dt = None
        if util.check_parameter(message[self._offset + 5 : self._offset + ALERT_SIZE]):
            to_dt = _convert_to_datetime(
                util.unpack_uint(message[self._offset + 5 : self._offset + ALERT_SIZE])[
                    0
                ]
            )

        self._offset += ALERT_SIZE

        return Alert(code, from_dt, to_dt)

    def decode(
        self, message: bytearray, offset: int = 0, data: EventDataType | None = None
    ) -> tuple[EventDataType, int]:
        """Decode bytes and return message data and offset."""
        start = message[offset + 1]
        end = message[offset + 2]
        self._offset = offset + 3
        return (
            ensure_device_data(
                data,
                {
                    ATTR_ALERTS: [
                        self._unpack_alert(message) for _ in range(start, start + end)
                    ]
                },
            ),
            self._offset,
        )
