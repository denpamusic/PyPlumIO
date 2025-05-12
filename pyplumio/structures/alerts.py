"""Contains an alerts structure decoder."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from typing import Any, Final, Literal, NamedTuple

from pyplumio.const import AlertType
from pyplumio.data_types import UnsignedInt
from pyplumio.structures import StructureDecoder
from pyplumio.utils import ensure_dict

ATTR_ALERTS: Final = "alerts"
ATTR_TOTAL_ALERTS: Final = "total_alerts"

MAX_UINT32: Final = 0xFFFFFFFF


class DateTimeInterval(NamedTuple):
    """Represents an alert time interval."""

    name: Literal["year", "month", "day", "hour", "minute", "second"]
    seconds: int
    offset: int = 0


DATETIME_INTERVALS: tuple[DateTimeInterval, ...] = (
    DateTimeInterval("year", seconds=60 * 60 * 24 * 31 * 12, offset=2000),
    DateTimeInterval("month", seconds=60 * 60 * 24 * 31, offset=1),
    DateTimeInterval("day", seconds=60 * 60 * 24, offset=1),
    DateTimeInterval("hour", seconds=60 * 60),
    DateTimeInterval("minute", seconds=60),
    DateTimeInterval("second", seconds=1),
)


@lru_cache(maxsize=10)
def seconds_to_datetime(timestamp: int) -> datetime:
    """Convert timestamp to a datetime object.

    The ecoMAX controller stores alert time as a special timestamp value
    in seconds counted from Jan 1st, 2000.
    """

    def datetime_kwargs(timestamp: int) -> Generator[Any, None, None]:
        """Yield a tuple, that represents a single datetime kwarg."""
        for name, seconds, offset in DATETIME_INTERVALS:
            value = timestamp // seconds
            timestamp -= value * seconds
            yield name, (value + offset)

    return datetime(**dict(datetime_kwargs(timestamp)))


@dataclass
class Alert:
    """Represents a device alert."""

    __slots__ = ("code", "from_dt", "to_dt")

    code: int
    from_dt: datetime
    to_dt: datetime | None


class AlertsStructure(StructureDecoder):
    """Represents an alerts data structure."""

    __slots__ = ("_offset",)

    _offset: int

    def _unpack_alert(self, message: bytearray) -> Alert:
        """Unpack an alert."""
        offset = self._offset
        code = message[offset]
        offset += 1
        from_seconds = UnsignedInt.from_bytes(message, offset)
        offset += from_seconds.size
        to_seconds = UnsignedInt.from_bytes(message, offset)
        offset += to_seconds.size
        from_dt = seconds_to_datetime(from_seconds.value)
        to_dt = (
            None
            if to_seconds.value == MAX_UINT32
            else seconds_to_datetime(to_seconds.value)
        )
        with suppress(ValueError):
            code = AlertType(code)

        self._offset = offset
        return Alert(code, from_dt, to_dt)

    def decode(
        self, message: bytearray, offset: int = 0, data: dict[str, Any] | None = None
    ) -> tuple[dict[str, Any], int]:
        """Decode bytes and return message data and offset."""
        total_alerts = message[offset + 0]
        start = message[offset + 1]
        end = message[offset + 2]
        self._offset = offset + 3
        if end == 0:
            # No alerts found.
            return ensure_dict(data, {ATTR_TOTAL_ALERTS: total_alerts}), self._offset

        return (
            ensure_dict(
                data,
                {
                    ATTR_ALERTS: [
                        self._unpack_alert(message) for _ in range(start, start + end)
                    ],
                    ATTR_TOTAL_ALERTS: total_alerts,
                },
            ),
            self._offset,
        )


__all__ = ["AlertsStructure", "Alert"]
