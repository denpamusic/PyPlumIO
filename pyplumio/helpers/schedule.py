"""Contains a schedule helper classes."""


from collections.abc import Iterable, Iterator, MutableMapping
from dataclasses import dataclass
import datetime as dt
import math
from typing import Final, Literal

from pyplumio.const import STATE_OFF, STATE_ON
from pyplumio.devices import AddressableDevice
from pyplumio.helpers.factory import factory
from pyplumio.structures.schedules import collect_schedule_data

TIME_FORMAT: Final = "%H:%M"
START_OF_DAY: Final = "00:00"
END_OF_DAY: Final = "00:00"

STATE_NIGHT: Final = "night"
STATE_DAY: Final = "day"

ON_STATES: Final = (STATE_ON, STATE_DAY)
OFF_STATES: Final = (STATE_OFF, STATE_NIGHT)
ALLOWED_STATES: Final = ON_STATES + OFF_STATES


def _parse_interval(start: str, end: str) -> tuple[int, int]:
    """Parse an interval string.

    Intervals should be specified in '%H:%M' format.
    """
    start_dt = dt.datetime.strptime(start, TIME_FORMAT)
    end_dt = dt.datetime.strptime(end, TIME_FORMAT)
    start_of_day_dt = dt.datetime.strptime(START_OF_DAY, TIME_FORMAT)
    if end_dt == start_of_day_dt:
        # Upper bound of interval is midnight.
        end_dt += dt.timedelta(hours=23, minutes=30)

    if end_dt <= start_dt:
        raise ValueError(
            f"Invalid interval ({start}, {end}). Lower boundary must be less than upper."
        )

    start_index = math.floor((start_dt - start_of_day_dt).total_seconds() // (60 * 30))
    end_index = math.floor((end_dt - start_of_day_dt).total_seconds() // (60 * 30))

    return start_index, end_index


class ScheduleDay(MutableMapping):
    """Represents a single day of schedule."""

    __slots__ = ("_intervals",)

    _intervals: list[bool]

    def __init__(self, intervals: list[bool]):
        """Initialize a new schedule day."""
        self._intervals = intervals

    def __repr__(self) -> str:
        """Return serializable representation of the class."""
        return f"ScheduleDay({self._intervals})"

    def __len__(self) -> int:
        """Return a schedule length."""
        return len(self._intervals)

    def __iter__(self) -> Iterator[bool]:
        """Return an iterator."""
        return self._intervals.__iter__()

    def __getitem__(self, index):
        """Return a schedule item."""
        return self._intervals.__getitem__(index)

    def __delitem__(self, index) -> None:
        """Delete a schedule item."""
        return self._intervals.__delitem__(index)

    def __setitem__(self, index, value) -> None:
        """Set a schedule item."""
        return self._intervals.__setitem__(index, value)

    def append(self, item) -> None:
        """Append a value to the interval."""
        self._intervals.append(item)

    def set_state(
        self,
        state: Literal["on", "off", "day", "night"],
        start: str = START_OF_DAY,
        end: str = END_OF_DAY,
    ) -> None:
        """Set an interval state.

        Can be on of the following:
        'on', 'off', 'day' or 'night'.
        """
        if state not in ALLOWED_STATES:
            raise ValueError(f'state "{state}" is not allowed')

        index, end_index = _parse_interval(start, end)
        while index <= end_index:
            self._intervals[index] = state in ON_STATES
            index += 1

    def set_on(self, start: str = START_OF_DAY, end: str = END_OF_DAY) -> None:
        """Set an interval state to 'on'."""
        self.set_state(STATE_ON, start, end)

    def set_off(self, start: str = START_OF_DAY, end: str = END_OF_DAY) -> None:
        """Set an interval state to 'off'."""
        self.set_state(STATE_OFF, start, end)

    @property
    def intervals(self) -> list[bool]:
        """A list of schedule intervals."""
        return self._intervals


@dataclass
class Schedule(Iterable):
    """Represents a weekly schedule."""

    __slots__ = (
        "name",
        "device",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    )

    name: str
    device: AddressableDevice
    monday: ScheduleDay
    tuesday: ScheduleDay
    wednesday: ScheduleDay
    thursday: ScheduleDay
    friday: ScheduleDay
    saturday: ScheduleDay
    sunday: ScheduleDay

    def __iter__(self) -> Iterator[ScheduleDay]:
        """Returns a list of days."""
        return (
            self.sunday,
            self.monday,
            self.tuesday,
            self.wednesday,
            self.thursday,
            self.friday,
            self.saturday,
        ).__iter__()

    def commit(self) -> None:
        """Commit a weekly schedule to the device."""
        self.device.queue.put_nowait(
            factory(
                "frames.requests.SetScheduleRequest",
                recipient=self.device.address,
                data=collect_schedule_data(self.name, self.device),
            )
        )
