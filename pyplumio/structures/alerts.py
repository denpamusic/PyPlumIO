"""Contains alarms structure decoder."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from pyplumio import util
from pyplumio.const import ATTR_ALERTS
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures import StructureDecoder, make_device_data


def _convert_to_datetime(seconds: int) -> datetime:
    """Converts timestamp to datetime."""
    intervals = (
        ("year", 32140800),  # 60 * 60 * 24 * 31 * 12
        ("month", 2678400),  # 60 * 60 * 24 * 31
        ("day", 86400),  # 60 * 60 * 24
        ("hour", 3600),  # 60 * 60
        ("minute", 60),
        ("second", 1),
    )

    result: Dict[str, int] = {}

    for name, count in intervals:
        value = seconds // count
        seconds -= value * count
        result[name] = value

    return datetime(
        year=(result["year"] + 2000),
        month=(result["month"] + 1),
        day=(result["day"] + 1),
        hour=result["hour"],
        minute=result["minute"],
        second=result["second"],
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
        first_alert = message[offset + 1]
        alerts_number = message[offset + 2]
        offset += 3
        alerts: List[Alert] = []
        for _ in range(first_alert, first_alert + alerts_number):
            code = message[offset]
            from_ts = util.unpack_uint(message[offset + 1 : offset + 5])[0]
            from_dt = _convert_to_datetime(from_ts)
            to_dt = None
            if util.check_parameter(message[offset + 5 : offset + 9]):
                to_ts = util.unpack_uint(message[offset + 5 : offset + 9])[0]
                to_dt = _convert_to_datetime(to_ts)

            alerts.append(Alert(code, from_dt, to_dt))
            offset += 9

        return make_device_data(data, {ATTR_ALERTS: alerts}), offset
