"""Contains schedule decoder."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, MutableMapping, Sequence
from dataclasses import dataclass
import datetime as dt
from functools import lru_cache, reduce
from typing import Annotated, Any, Final, get_args

from pyplumio.const import (
    ATTR_PARAMETER,
    ATTR_SCHEDULE,
    ATTR_SWITCH,
    ATTR_TYPE,
    STATE_OFF,
    STATE_ON,
    FrameType,
    State,
)
from pyplumio.devices import Device, PhysicalDevice
from pyplumio.exceptions import FrameDataError
from pyplumio.frames import Request
from pyplumio.parameters import (
    Number,
    NumberDescription,
    Parameter,
    ParameterDescription,
    ParameterValues,
    Switch,
    SwitchDescription,
    unpack_parameter,
)
from pyplumio.structures import Structure
from pyplumio.utils import ensure_dict

ATTR_SCHEDULES: Final = "schedules"
ATTR_SCHEDULE_PARAMETERS: Final = "schedule_parameters"
ATTR_SCHEDULE_SWITCH: Final = "schedule_switch"
ATTR_SCHEDULE_PARAMETER: Final = "schedule_parameter"

SCHEDULE_SIZE: Final = 42  # 6 bytes per day, 7 days total

SCHEDULES: tuple[str, ...] = (
    "heating",
    "water_heater",
    "circulation_pump",
    "boiler_work",
    "boiler_clean",
    "hear_exchanger_clean",
    "mixer_1",
    "mixer_2",
    "mixer_3",
    "mixer_4",
    "mixer_5",
    "mixer_6",
    "mixer_7",
    "mixer_8",
    "mixer_9",
    "mixer_10",
    "thermostat_1",
    "thermostat_2",
    "thermostat_3",
    "circuit_1",
    "circuit_2",
    "circuit_3",
    "circuit_4",
    "circuit_5",
    "circuit_6",
    "circuit_7",
    "panel_1",
    "panel_2",
    "panel_3",
    "panel_4",
    "panel_5",
    "panel_6",
    "panel_7",
    "main_heater_solar",
    "heating_circulation",
    "internal_thermostat",
    "heater",
    "water_heater_2",
    "intake",
    "intake_summer",
)


@dataclass
class ScheduleParameterDescription(ParameterDescription):
    """Represent a schedule parameter description."""


class ScheduleParameter(Parameter):
    """Represents a schedule parameter."""

    __slots__ = ()

    device: PhysicalDevice
    description: ScheduleParameterDescription

    async def create_request(self) -> Request:
        """Create a request to change the parameter."""
        schedule_name = self.description.name.split("_schedule_", 1)[0]
        return await Request.create(
            FrameType.REQUEST_SET_SCHEDULE,
            recipient=self.device.address,
            data=collect_schedule_data(schedule_name, self.device),
        )


@dataclass(slots=True)
class ScheduleNumberDescription(ScheduleParameterDescription, NumberDescription):
    """Represents a schedule number description."""


class ScheduleNumber(ScheduleParameter, Number):
    """Represents a schedule number."""

    __slots__ = ()

    description: ScheduleNumberDescription


@dataclass(slots=True)
class ScheduleSwitchDescription(ScheduleParameterDescription, SwitchDescription):
    """Represents a schedule switch description."""


class ScheduleSwitch(ScheduleParameter, Switch):
    """Represents a schedule switch."""

    __slots__ = ()

    description: ScheduleSwitchDescription


SCHEDULE_PARAMETERS: list[ScheduleParameterDescription] = [
    description
    for name in SCHEDULES
    for description in [
        ScheduleSwitchDescription(name=f"{name}_{ATTR_SCHEDULE_SWITCH}"),
        ScheduleNumberDescription(name=f"{name}_{ATTR_SCHEDULE_PARAMETER}"),
    ]
]


def collect_schedule_data(name: str, device: Device) -> dict[str, Any]:
    """Return a schedule data collected from the device."""
    return {
        ATTR_TYPE: name,
        ATTR_SWITCH: device.data[f"{name}_{ATTR_SCHEDULE_SWITCH}"],
        ATTR_PARAMETER: device.data[f"{name}_{ATTR_SCHEDULE_PARAMETER}"],
        ATTR_SCHEDULE: device.data[ATTR_SCHEDULES][name],
    }


TIME_FORMAT: Final = "%H:%M"

Time = Annotated[str, "Time string in %H:%M format"]

MIDNIGHT: Final = Time("00:00")
MIDNIGHT_DT = dt.datetime.strptime(MIDNIGHT, TIME_FORMAT)

STEP = dt.timedelta(minutes=30)


def get_time(
    index: int, start: dt.datetime = MIDNIGHT_DT, step: dt.timedelta = STEP
) -> Time:
    """Return time for a specific index."""
    time_dt = start + (step * index)
    return f"{time_dt.hour:02d}:{time_dt.minute:02d}"


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


@dataclass(slots=True)
class Schedule(Iterable):
    """Represents a weekly schedule."""

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


def _split_byte(byte: int) -> list[bool]:
    """Split single byte into an eight bits."""
    return [bool(byte & (1 << bit)) for bit in reversed(range(8))]


def _join_bits(bits: Sequence[int | bool]) -> int:
    """Join eight bits into a single byte."""
    return reduce(lambda bit, byte: (bit << 1) | byte, bits)


class SchedulesStructure(Structure):
    """Represents a schedule data structure."""

    __slots__ = ("_offset",)

    _offset: int

    def encode(self, data: dict[str, Any]) -> bytearray:
        """Encode data to the bytearray message."""
        try:
            header = bytearray(
                b"\1"
                + SCHEDULES.index(data[ATTR_TYPE]).to_bytes(
                    length=1, byteorder="little"
                )
                + int(data[ATTR_SWITCH]).to_bytes(length=1, byteorder="little")
                + int(data[ATTR_PARAMETER]).to_bytes(length=1, byteorder="little")
            )
            schedule = data[ATTR_SCHEDULE]
        except (KeyError, ValueError) as e:
            raise FrameDataError from e

        return header + bytearray(
            _join_bits(day[i : i + 8])
            for day in schedule
            for i in range(0, len(day), 8)
        )

    def _unpack_schedule(self, message: bytearray) -> list[list[bool]]:
        """Unpack a schedule."""
        offset = self._offset
        schedule = [
            bit
            for i in range(offset, offset + SCHEDULE_SIZE)
            for bit in _split_byte(message[i])
        ]
        self._offset = offset + SCHEDULE_SIZE
        # Split the schedule. Each day consists of 48 half-hour intervals.
        return [schedule[i : i + 48] for i in range(0, len(schedule), 48)]

    def decode(
        self, message: bytearray, offset: int = 0, data: dict[str, Any] | None = None
    ) -> tuple[dict[str, Any], int]:
        """Decode bytes and return message data and offset."""
        try:
            start = message[offset + 1]
            end = message[offset + 2]
        except IndexError:
            return ensure_dict(data, {ATTR_SCHEDULES: []}), offset

        schedules: list[tuple[int, list[list[bool]]]] = []
        parameters: list[tuple[int, ParameterValues]] = []

        self._offset = offset + 3
        for _ in range(start, start + end):
            index = message[self._offset]
            switch = ParameterValues(
                value=message[self._offset + 1], min_value=0, max_value=1
            )
            parameter = unpack_parameter(message, self._offset + 2)
            self._offset += 5
            schedules.append((index, self._unpack_schedule(message)))
            parameters.append((index * 2, switch))
            if parameter is not None:
                parameters.append((index * 2 + 1, parameter))

        return (
            ensure_dict(
                data, {ATTR_SCHEDULES: schedules, ATTR_SCHEDULE_PARAMETERS: parameters}
            ),
            self._offset,
        )


__all__ = [
    "ATTR_SCHEDULES",
    "ATTR_SCHEDULE_PARAMETERS",
    "ATTR_SCHEDULE_SWITCH",
    "ATTR_SCHEDULE_PARAMETER",
    "Schedule",
    "ScheduleDay",
    "ScheduleParameterDescription",
    "ScheduleParameter",
    "ScheduleNumberDescription",
    "ScheduleNumber",
    "ScheduleSwitchDescription",
    "ScheduleSwitch",
    "SCHEDULE_PARAMETERS",
    "collect_schedule_data",
    "SchedulesStructure",
]
