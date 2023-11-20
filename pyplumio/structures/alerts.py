"""Contains an alerts structure decoder."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from typing import Any, Final, Generator

from pyplumio.const import AlertType
from pyplumio.helpers.data_types import UnsignedInt
from pyplumio.helpers.typing import EventDataType
from pyplumio.structures import StructureDecoder
from pyplumio.utils import ensure_dict

ATTR_ALERTS: Final = "alerts"


@lru_cache(maxsize=10)
def _convert_to_datetime(seconds: int) -> datetime:
    """Convert timestamp to a datetime object."""

    def _seconds_to_datetime_args(seconds: int) -> Generator[Any, None, None]:
        """Convert seconds to a kwargs for a datetime class."""
        intervals: tuple[tuple[str, int, int], ...] = (
            ("year", 32140800, 2000),  # 60sec * 60min * 24h * 31d * 12m
            ("month", 2678400, 1),  # 60sec * 60min * 24h * 31d
            ("day", 86400, 1),  # 60sec * 60min * 24h
            ("hour", 3600, 0),  # 60sec * 60min
            ("minute", 60, 0),
            ("second", 1, 0),
        )

        for name, count, offset in intervals:
            value = seconds // count
            seconds -= value * count
            yield name, (value + offset)

    return datetime(**dict(_seconds_to_datetime_args(seconds)))


@dataclass
class Alert:
    """Represents a device alert."""

    __slots__ = ("code", "from_dt", "to_dt")

    code: int
    from_dt: datetime
    to_dt: datetime | None


class AlertsStructure(StructureDecoder):
    """Represents an alerts data structure."""

    _offset: int

    def _unpack_alert(self, message: bytearray) -> Alert:
        """Unpack an alert."""
        try:
            code = message[self._offset]
            code = AlertType(code)
        except ValueError:
            pass

        self._offset += 1
        from_seconds = UnsignedInt.from_bytes(message, self._offset)
        self._offset += from_seconds.size
        to_seconds = UnsignedInt.from_bytes(message, self._offset)
        self._offset += to_seconds.size

        from_dt = _convert_to_datetime(from_seconds.value)
        to_dt = _convert_to_datetime(to_seconds.value) if to_seconds.value > 0 else None

        return Alert(code, from_dt, to_dt)

    def decode(
        self, message: bytearray, offset: int = 0, data: EventDataType | None = None
    ) -> tuple[EventDataType, int]:
        """Decode bytes and return message data and offset."""
        start = message[offset + 1]
        end = message[offset + 2]

        if end == 0:
            # No alerts found.
            return ensure_dict(data), offset + 1

        self._offset = offset + 3
        return (
            ensure_dict(
                data,
                {
                    ATTR_ALERTS: [
                        self._unpack_alert(message) for _ in range(start, start + end)
                    ]
                },
            ),
            self._offset,
        )
