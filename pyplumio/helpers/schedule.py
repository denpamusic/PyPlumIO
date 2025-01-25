"""Contains a schedule helper classes."""

from __future__ import annotations

from collections.abc import Generator, Iterable, Iterator, MutableMapping
from dataclasses import dataclass
import datetime as dt
from functools import lru_cache
import math
from typing import Annotated, Final, Literal, get_args

from typing_extensions import TypeAlias

from pyplumio.const import STATE_OFF, STATE_ON, FrameType
from pyplumio.devices import PhysicalDevice
from pyplumio.frames import Request
from pyplumio.structures.schedules import collect_schedule_data

TIME_FORMAT: Final = "%H:%M"

STATE_NIGHT: Final = "night"
STATE_DAY: Final = "day"

ON_STATES: Final = (STATE_ON, STATE_DAY)
OFF_STATES: Final = (STATE_OFF, STATE_NIGHT)

ScheduleState: TypeAlias = Literal["on", "off", "day", "night"]
Time = Annotated[str, "time in HH:MM format"]

start_of_day_dt = dt.datetime.strptime("00:00", TIME_FORMAT)


def _get_time_range(
    start: Time, end: Time, step: int = 30
) -> Generator[int, None, None]:
    """Get a time range.

    Start and end times should be specified in HH:MM format, step in
    minutes.
    """

    @lru_cache(maxsize=10)
    def _get_time_range_cached(start: Time, end: Time, step: int = 30) -> range:
        """Get a time range and cache it using LRU cache."""
        start_dt = dt.datetime.strptime(start, TIME_FORMAT)
        end_dt = dt.datetime.strptime(end, TIME_FORMAT)
        if end_dt == start_of_day_dt:
            # Upper boundary of the interval is midnight.
            end_dt += dt.timedelta(hours=24) - dt.timedelta(minutes=step)

        if end_dt <= start_dt:
            raise ValueError(
                f"Invalid time range: start time ({start}) must be earlier "
                f"than end time ({end})."
            )

        def _dt_to_index(dt: dt.datetime) -> int:
            """Convert datetime to index in schedule list."""
            return math.floor((dt - start_of_day_dt).total_seconds() // (60 * step))

        return range(_dt_to_index(start_dt), _dt_to_index(end_dt) + 1)

    yield from _get_time_range_cached(start, end, step)


class ScheduleDay(MutableMapping):
    """Represents a single day of schedule."""

    __slots__ = ("_intervals",)

    _intervals: list[bool]

    def __init__(self, intervals: list[bool]) -> None:
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

    def __getitem__(self, index: int) -> bool:
        """Return a schedule item."""
        return self._intervals.__getitem__(index)

    def __delitem__(self, index: int) -> None:
        """Delete a schedule item."""
        return self._intervals.__delitem__(index)

    def __setitem__(self, index: int, value: bool) -> None:
        """Set a schedule item."""
        return self._intervals.__setitem__(index, value)

    def append(self, item: bool) -> None:
        """Append a value to the interval."""
        self._intervals.append(item)

    def set_state(
        self, state: ScheduleState, start: Time = "00:00", end: Time = "00:00"
    ) -> None:
        """Set a schedule interval state."""
        if state not in get_args(ScheduleState):
            raise ValueError(
                f"Invalid state '{state}'. Allowed states are: "
                f"{', '.join(get_args(ScheduleState))}"
            )

        for index in _get_time_range(start, end):
            self._intervals[index] = True if state in ON_STATES else False

    def set_on(self, start: Time = "00:00", end: Time = "00:00") -> None:
        """Set a schedule interval state to 'on'."""
        self.set_state(STATE_ON, start, end)

    def set_off(self, start: Time = "00:00", end: Time = "00:00") -> None:
        """Set a schedule interval state to 'off'."""
        self.set_state(STATE_OFF, start, end)

    @property
    def intervals(self) -> list[bool]:
        """Return the schedule intervals."""
        return self._intervals


@dataclass
class Schedule(Iterable):
    """Represents a weekly schedule."""

    __slots__ = (
        "name",
        "device",
        "sunday",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
    )

    name: str
    device: PhysicalDevice

    sunday: ScheduleDay
    monday: ScheduleDay
    tuesday: ScheduleDay
    wednesday: ScheduleDay
    thursday: ScheduleDay
    friday: ScheduleDay
    saturday: ScheduleDay

    def __iter__(self) -> Iterator[ScheduleDay]:
        """Return list of days."""
        return (
            self.sunday,
            self.monday,
            self.tuesday,
            self.wednesday,
            self.thursday,
            self.friday,
            self.saturday,
        ).__iter__()

    async def commit(self) -> None:
        """Commit a weekly schedule to the device."""
        await self.device.queue.put(
            await Request.create(
                FrameType.REQUEST_SET_SCHEDULE,
                recipient=self.device.address,
                data=collect_schedule_data(self.name, self.device),
            )
        )
