"""Contains tests for the schedules structure decoder."""

from __future__ import annotations

import asyncio
import datetime as dt
from typing import Literal, cast
from unittest.mock import Mock, patch

import pytest

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
from pyplumio.devices import DeviceType, PhysicalDevice
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.structures.schedules import (
    ATTR_SCHEDULE_PARAMETER,
    ATTR_SCHEDULE_SWITCH,
    ATTR_SCHEDULES,
    MIDNIGHT,
    MIDNIGHT_DT,
    STEP,
    TIME_FORMAT,
    Schedule,
    ScheduleDay,
    Time,
    collect_schedule_data,
    get_time,
    get_time_range,
)
from tests.conftest import RAISES


def test_collect_schedule_data(ecomax: EcoMAX) -> None:
    """Test collecting schedule data."""
    schedule_name = "heating"
    ecomax.data |= {
        f"{schedule_name}_{ATTR_SCHEDULE_SWITCH}": 1,
        f"{schedule_name}_{ATTR_SCHEDULE_PARAMETER}": 2,
        ATTR_SCHEDULES: {schedule_name: {"test": 1}},
    }
    data = collect_schedule_data(schedule_name, ecomax)
    assert data == {
        "parameter": 2,
        "schedule": {"test": 1},
        "switch": 1,
        "type": "heating",
    }


@pytest.mark.parametrize(
    ("index", "start", "step", "expected_time"),
    [
        (1, MIDNIGHT_DT, STEP, Time("00:30")),
        (47, MIDNIGHT_DT, STEP, Time("23:30")),
        (1, dt.datetime.strptime("01:00", TIME_FORMAT), STEP, Time("01:30")),
        (47, dt.datetime.strptime("01:00", TIME_FORMAT), STEP, Time("00:30")),
        (1, MIDNIGHT_DT, dt.timedelta(minutes=15), Time("00:15")),
    ],
)
def test_get_time(
    index: int, start: dt.datetime, step: dt.timedelta, expected_time: Time
) -> None:
    """Test returning time for a specific index."""
    assert get_time(index, start=start, step=step) == expected_time


@pytest.mark.parametrize(
    ("start", "end", "step", "expected_range"),
    [
        (
            Time("00:00"),
            Time("01:00"),
            STEP,
            [Time("00:00"), Time("00:30"), Time("01:00")],
        ),
        (
            Time("00:00"),
            Time("00:30"),
            dt.timedelta(minutes=15),
            [Time("00:00"), Time("00:15"), Time("00:30")],
        ),
        (
            Time("00:00"),
            Time("00:30"),
            dt.timedelta(minutes=20),
            [Time("00:00"), Time("00:20")],
        ),
        (
            Time("00:00"),
            Time("00:00"),
            dt.timedelta(hours=12),
            [Time("00:00"), Time("12:00")],
        ),
    ],
)
def test_get_time_range(
    start: Time, end: Time, step: dt.timedelta, expected_range: list[Time]
) -> None:
    """Test getting the time range."""
    assert get_time_range(start=start, end=end, step=step) == expected_range


def test_get_time_invalid() -> None:
    """Test getting the time range with invalid boundaries."""
    with pytest.raises(ValueError, match="Invalid time range"):
        get_time_range(start=Time("01:00"), end=Time("00:30"))


@pytest.fixture(name="intervals")
def fixture_intervals() -> list[Time]:
    """Return time intervals for a schedule day."""
    return (
        "00:00, 00:30, 01:00, 01:30, 02:00, 02:30, 03:00, 03:30, 04:00, 04:30, 05:00, "
        "05:30, 06:00, 06:30, 07:00, 07:30, 08:00, 08:30, 09:00, 09:30, 10:00, 10:30, "
        "11:00, 11:30, 12:00, 12:30, 13:00, 13:30, 14:00, 14:30, 15:00, 15:30, 16:00, "
        "16:30, 17:00, 17:30, 18:00, 18:30, 19:00, 19:30, 20:00, 20:30, 21:00, 21:30, "
        "22:00, 22:30, 23:00, 23:30"
    ).split(", ")


@pytest.fixture(name="schedule_day")
def fixture_schedule_day() -> ScheduleDay:
    """Return a schedule day object."""
    schedule_day = ScheduleDay.from_iterable([False for _ in range(48)])
    assert len(schedule_day) == 48
    return schedule_day


class TestScheduleDay:
    """Contains tests for ScheduleDay class."""

    @pytest.mark.parametrize(
        ("start", "end", "state", "error_pattern"),
        [
            (Time("00:00"), Time("01:00"), STATE_ON, None),
            (Time("01:00"), Time("10:00"), STATE_OFF, None),
            (Time("01:00"), Time("00:30"), RAISES, "Invalid time range"),
            (Time("00:foo"), Time("bar"), RAISES, "%H:%M"),
            (Time("05:00"), Time("18:00"), RAISES, "on, off"),
        ],
    )
    def test_set_state(
        self,
        start: Time,
        end: Time,
        state: Literal["on", "off", "raises"],
        error_pattern: str | None,
        schedule_day: ScheduleDay,
    ) -> None:
        """Test setting a state."""
        if state == RAISES:
            with pytest.raises((ValueError, TypeError), match=error_pattern):
                schedule_day.set_state(state, start, end)  # type: ignore[arg-type]
            return

        schedule_day.set_state(state, start, end)
        assert schedule_day[start] == state
        assert schedule_day[end] == state
        if state == STATE_ON:
            schedule_day[start] = STATE_OFF
            assert schedule_day.schedule[start] is False
        else:
            schedule_day[start] = STATE_ON
            assert schedule_day.schedule[start] is True

    def test_set_whole_day_schedule(
        self, schedule_day: ScheduleDay, intervals: list[Time]
    ) -> None:
        """Test setting schedule for a whole day."""
        schedule_day.set_on()
        assert schedule_day.schedule == dict.fromkeys(intervals, True)
        schedule_day.set_off()
        assert schedule_day.schedule == dict.fromkeys(intervals, False)

    def test_repr(self, schedule_day: ScheduleDay, intervals: list[Time]) -> None:
        """Test serializable representation of a schedule day."""
        schedule = dict.fromkeys(intervals, False)
        assert repr(schedule_day) == (f"ScheduleDay({schedule})")

    def test_iter(self, schedule_day: ScheduleDay) -> None:
        """Test setting schedule using iterable methods."""
        expected_times = list(schedule_day.schedule.keys())
        iterated_times = list(iter(schedule_day))
        assert iterated_times == expected_times

    def test_mapping(self, schedule_day: ScheduleDay) -> None:
        """Test mutable mapping methods."""
        assert schedule_day[MIDNIGHT] == STATE_OFF
        schedule_day[MIDNIGHT] = True
        assert schedule_day[MIDNIGHT] == STATE_ON
        del schedule_day[MIDNIGHT]
        assert len(schedule_day) == 47
        assert MIDNIGHT not in schedule_day


@pytest.fixture(name="schedule")
def fixture_schedule(schedule_day: ScheduleDay) -> Schedule:
    """Return a schedule object."""
    return Schedule(
        name="test",
        device=Mock(spec=PhysicalDevice, autospec=True),
        monday=ScheduleDay.from_iterable([True for _ in range(48)]),
        tuesday=schedule_day,
        wednesday=schedule_day,
        thursday=schedule_day,
        friday=schedule_day,
        saturday=schedule_day,
        sunday=schedule_day,
    )


class TestSchedule:
    """Contains tests for Schedule class."""

    @pytest.mark.parametrize(
        ("day", "time", "state"),
        [
            ("sunday", MIDNIGHT, STATE_OFF),
            ("monday", MIDNIGHT, STATE_ON),
            ("tuesday", MIDNIGHT, STATE_OFF),
            ("wednesday", MIDNIGHT, STATE_OFF),
            ("thursday", MIDNIGHT, STATE_OFF),
            ("friday", MIDNIGHT, STATE_OFF),
            ("saturday", MIDNIGHT, STATE_OFF),
        ],
    )
    def test_get(self, day: str, time: Time, state: State, schedule: Schedule) -> None:
        """Test getting a schedule day."""
        schedule_day = cast(ScheduleDay, getattr(schedule, day))
        assert schedule_day[time] == state

    def test_iter(self, schedule: Schedule) -> None:
        """Test a schedule."""
        expected_days = [
            schedule.sunday,
            schedule.monday,
            schedule.tuesday,
            schedule.wednesday,
            schedule.thursday,
            schedule.friday,
            schedule.saturday,
        ]
        iterated_days = list(iter(schedule))
        assert iterated_days == expected_days

    @patch("pyplumio.structures.schedules.Request.create")
    async def test_commit(self, mock_request_create, schedule: Schedule) -> None:
        """Test committing a schedule."""
        mock_device = Mock(spec=PhysicalDevice, autospec=True)
        mock_device.address = DeviceType.ECOMAX
        mock_device.data = {
            f"test_{ATTR_SCHEDULE_SWITCH}": 1,
            f"test_{ATTR_SCHEDULE_PARAMETER}": 2,
            ATTR_SCHEDULES: {"test": schedule},
        }
        mock_device.queue = Mock(spec=asyncio.Queue, autospec=True)
        schedule.device = mock_device
        await schedule.commit()
        mock_request_create.assert_awaited_once_with(
            FrameType.REQUEST_SET_SCHEDULE,
            recipient=mock_device.address,
            data={
                ATTR_TYPE: "test",
                ATTR_SWITCH: 1,
                ATTR_PARAMETER: 2,
                ATTR_SCHEDULE: schedule,
            },
        )
