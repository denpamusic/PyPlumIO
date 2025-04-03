"""Contains tests for the schedule helper classes."""

import asyncio
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
)
from pyplumio.devices import Device, DeviceType
from pyplumio.helpers.schedule import Schedule, ScheduleDay, Time
from pyplumio.structures.schedules import (
    ATTR_SCHEDULE_PARAMETER,
    ATTR_SCHEDULE_SWITCH,
    ATTR_SCHEDULES,
)


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


@pytest.fixture(name="schedule")
def fixture_schedule(schedule_day: ScheduleDay) -> Schedule:
    """Return a schedule object."""
    return Schedule(
        name="test",
        device=Mock(spec=Device),
        monday=ScheduleDay.from_iterable([True for _ in range(48)]),
        tuesday=schedule_day,
        wednesday=schedule_day,
        thursday=schedule_day,
        friday=schedule_day,
        saturday=schedule_day,
        sunday=schedule_day,
    )


def test_schedule_day(schedule_day: ScheduleDay) -> None:
    """Test a schedule day."""
    schedule_day.set_state(STATE_ON, "00:00", "01:00")
    for time in ("00:00", "00:30", "01:00"):
        assert schedule_day[time] == STATE_ON
    assert schedule_day["01:30"] == schedule_day["02:00"] == STATE_OFF
    schedule_day["02:00"] = STATE_ON
    assert schedule_day.schedule["02:00"]


def test_schedule_day_with_missing_key(schedule_day: ScheduleDay) -> None:
    """Test a schedule day with a missing key."""
    with pytest.raises(KeyError):
        assert schedule_day["00:20"] == STATE_OFF


def test_schedule_day_with_incorrect_interval(schedule_day: ScheduleDay) -> None:
    """Test a schedule day with an incorrect interval."""
    for start, end in (("01:00", "00:30"), ("00:foo", "bar")):
        with pytest.raises(ValueError):
            schedule_day.set_state(STATE_ON, start, end)


def test_schedule_day_with_incorrect_state(schedule_day: ScheduleDay) -> None:
    """Test a schedule day with an incorrect state."""
    with pytest.raises(TypeError):
        schedule_day.set_state("invalid_state", "00:00", "01:00")  # type: ignore[arg-type]


def test_setting_whole_day_schedule(
    schedule_day: ScheduleDay, intervals: list[Time]
) -> None:
    """Test setting schedule for a whole day."""
    schedule_day.set_on()
    assert schedule_day.schedule == dict.fromkeys(intervals, True)
    schedule_day.set_off()
    assert schedule_day.schedule == dict.fromkeys(intervals, False)


def test_setting_schedule_as_iterable(schedule_day: ScheduleDay) -> None:
    """Test setting schedule using iterable methods."""
    schedule_day.set_on("00:30", "01:00")
    schedule_day_iter = iter(schedule_day)
    assert schedule_day[next(schedule_day_iter)] == STATE_OFF
    assert schedule_day[next(schedule_day_iter)] == STATE_ON
    assert "00:30" in schedule_day
    assert schedule_day["00:30"] == STATE_ON
    schedule_day["00:30"] = STATE_OFF
    del schedule_day["00:00"]
    assert len(schedule_day) == 47
    assert "00:00" not in schedule_day


def test_schedule_day_repr(schedule_day: ScheduleDay, intervals: list[Time]) -> None:
    """Test serializable representation of a schedule day."""
    schedule = dict.fromkeys(intervals, False)
    assert repr(schedule_day) == (f"ScheduleDay({schedule})")


def test_schedule(schedule: Schedule) -> None:
    """Test a schedule."""
    schedule_iter = iter(schedule)
    assert next(schedule_iter)["00:00"] == STATE_OFF
    assert next(schedule_iter)["00:00"] == STATE_ON


@patch("pyplumio.helpers.schedule.Request.create")
async def test_schedule_commit(mock_request_create, schedule: Schedule) -> None:
    """Test committing a schedule."""
    schedule.device = Mock(spec=Device)
    schedule.device.address = DeviceType.ECOMAX
    schedule.device.data = {
        f"test_{ATTR_SCHEDULE_SWITCH}": 1,
        f"test_{ATTR_SCHEDULE_PARAMETER}": 2,
        ATTR_SCHEDULES: {"test": schedule},
    }
    schedule.device.queue = Mock(spec=asyncio.Queue)

    await schedule.commit()
    mock_request_create.assert_awaited_once_with(
        FrameType.REQUEST_SET_SCHEDULE,
        recipient=DeviceType.ECOMAX,
        data={
            ATTR_TYPE: "test",
            ATTR_SWITCH: 1,
            ATTR_PARAMETER: 2,
            ATTR_SCHEDULE: schedule,
        },
    )
