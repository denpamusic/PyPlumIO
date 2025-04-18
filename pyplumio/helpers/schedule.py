"""Contains a schedule helper classes."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, MutableMapping
from dataclasses import dataclass
import datetime as dt
from functools import lru_cache
from typing import Annotated, Final, get_args

from pyplumio.const import STATE_OFF, STATE_ON, FrameType, State
from pyplumio.devices import PhysicalDevice
from pyplumio.frames import Request
from pyplumio.structures.schedules import collect_schedule_data

TIME_FORMAT: Final = "%H:%M"

MIDNIGHT: Final = "00:00"
MIDNIGHT_DT = dt.datetime.strptime(MIDNIGHT, TIME_FORMAT)

STEP = dt.timedelta(minutes=30)

Time = Annotated[str, "Time string in %H:%M format"]


def get_time(
    index: int, start: dt.datetime = MIDNIGHT_DT, step: dt.timedelta = STEP
) -> Time:
    """Return time for a specific index."""
    time_dt = start + (step * index)
    return time_dt.strftime(TIME_FORMAT)


@lru_cache(maxsize=10)
def get_time_range(start: Time, end: Time, step: dt.timedelta = STEP) -> list[Time]:
    """Get a time range.

    Start and end boundaries should be specified in %H:%M format.
    Both are inclusive.
    """
    start_dt = dt.datetime.strptime(start, TIME_FORMAT)
    end_dt = dt.datetime.strptime(end, TIME_FORMAT)

    if end_dt == MIDNIGHT_DT:
        # Upper boundary of the interval is midnight.
        end_dt += dt.timedelta(hours=24) - step

    if end_dt <= start_dt:
        raise ValueError(
            f"Invalid time range: start time ({start}) must be earlier "
            f"than end time ({end})."
        )

    seconds = (end_dt - start_dt).total_seconds()
    steps = seconds // step.total_seconds() + 1

    return [get_time(index, start=start_dt, step=step) for index in range(int(steps))]


class ScheduleDay(MutableMapping):
    """Represents a single day of schedule."""

    __slots__ = ("_schedule",)

    _schedule: dict[Time, bool]

    def __init__(self, schedule: dict[Time, bool]) -> None:
        """Initialize a new schedule day."""
        self._schedule = schedule

    def __repr__(self) -> str:
        """Return serializable representation of the class."""
        return f"ScheduleDay({self._schedule})"

    def __len__(self) -> int:
        """Return a schedule length."""
        return self._schedule.__len__()

    def __iter__(self) -> Iterator[Time]:
        """Return an iterator."""
        return self._schedule.__iter__()

    def __getitem__(self, time: Time) -> State:
        """Return a schedule item."""
        state = self._schedule.__getitem__(time)
        return STATE_ON if state else STATE_OFF

    def __delitem__(self, time: Time) -> None:
        """Delete a schedule item."""
        self._schedule.__delitem__(time)

    def __setitem__(self, time: Time, state: State | bool) -> None:
        """Set a schedule item."""
        if state in get_args(State):
            state = True if state == STATE_ON else False
        if isinstance(state, bool):
            self._schedule.__setitem__(time, state)
        else:
            raise TypeError(
                f"Expected boolean value or one of: {', '.join(get_args(State))}."
            )

    def set_state(
        self, state: State | bool, start: Time = MIDNIGHT, end: Time = MIDNIGHT
    ) -> None:
        """Set a schedule interval state."""
        for time in get_time_range(start, end):
            self.__setitem__(time, state)

    def set_on(self, start: Time = MIDNIGHT, end: Time = MIDNIGHT) -> None:
        """Set a schedule interval state to 'on'."""
        self.set_state(STATE_ON, start, end)

    def set_off(self, start: Time = MIDNIGHT, end: Time = MIDNIGHT) -> None:
        """Set a schedule interval state to 'off'."""
        self.set_state(STATE_OFF, start, end)

    @property
    def schedule(self) -> dict[Time, bool]:
        """Return the schedule."""
        return self._schedule

    @classmethod
    def from_iterable(cls: type[ScheduleDay], intervals: Iterable[bool]) -> ScheduleDay:
        """Make schedule day from iterable."""
        return cls({get_time(index): state for index, state in enumerate(intervals)})


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


__all__ = ["Schedule", "ScheduleDay"]
