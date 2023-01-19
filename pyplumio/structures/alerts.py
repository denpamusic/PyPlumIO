"""Contains alarms structure decoder."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Final, List, Optional, Tuple

from pyplumio import util
from pyplumio.const import AlertType
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures import StructureDecoder, ensure_device_data

ATTR_ALERTS: Final = "alerts"
ATTR_YEAR: Final = "year"
ATTR_MONTH: Final = "month"
ATTR_DAY: Final = "day"
ATTR_HOUR: Final = "hour"
ATTR_MINUTE: Final = "minute"
ATTR_SECOND: Final = "second"


def _convert_to_datetime(seconds: int) -> datetime:
    """Converts timestamp to datetime."""
    intervals: Tuple[Tuple[str, int], ...] = (
        (ATTR_YEAR, 32140800),  # 60sec * 60min * 24h * 31d * 12m
        (ATTR_MONTH, 2678400),  # 60sec * 60min * 24h * 31d
        (ATTR_DAY, 86400),  # 60sec * 60min * 24h
        (ATTR_HOUR, 3600),  # 60sec * 60min
        (ATTR_MINUTE, 60),
        (ATTR_SECOND, 1),
    )

    result: Dict[str, int] = {}

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
    """Represents device alert."""

    code: int
    from_dt: datetime
    to_dt: Optional[datetime]


class AlertsStructure(StructureDecoder):
    """Represents alerts data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        first_index = message[offset + 1]
        last_index = message[offset + 2]
        offset += 3
        alerts: List[Alert] = []
        for _ in range(first_index, first_index + last_index):
            try:
                code = message[offset]
                code = AlertType(code)
            except ValueError:
                pass

            from_ts = util.unpack_uint(message[offset + 1 : offset + 5])[0]
            from_dt = _convert_to_datetime(from_ts)
            to_dt = None
            if util.check_parameter(message[offset + 5 : offset + 9]):
                to_ts = util.unpack_uint(message[offset + 5 : offset + 9])[0]
                to_dt = _convert_to_datetime(to_ts)

            alerts.append(Alert(code, from_dt, to_dt))
            offset += 9

        return ensure_device_data(data, {ATTR_ALERTS: alerts}), offset
