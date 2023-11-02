"""Contains tests for the schedule helper classes."""

import asyncio
from unittest.mock import Mock, patch

import pytest

from pyplumio.const import (
    ATTR_PARAMETER,
    ATTR_SCHEDULE,
    ATTR_SWITCH,
    ATTR_TYPE,
    STATE_ON,
)
from pyplumio.devices import Device, DeviceType
from pyplumio.helpers.schedule import Schedule, ScheduleDay
from pyplumio.structures.schedules import (
    ATTR_SCHEDULE_PARAMETER,
    ATTR_SCHEDULE_SWITCH,
    ATTR_SCHEDULES,
)


@pytest.fixture(name="schedule_day")
def fixture_schedule_day() -> ScheduleDay:
    """Return a schedule day object."""
    return ScheduleDay([False for _ in range(48)])


@pytest.fixture(name="schedule")
def fixture_schedule(schedule_day: ScheduleDay) -> Schedule:
    """Return a schedule object."""
    return Schedule(
        name="test",
        device=Mock(spec=Device),
        monday=ScheduleDay([True for _ in range(48)]),
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
    assert schedule_day.intervals[0]  # 00:00
    assert schedule_day.intervals[1]  # 00:30
    assert schedule_day.intervals[2]  # 01:00
    assert not schedule_day.intervals[3]  # 01:30
    assert len(schedule_day) == 48


def test_schedule_day_with_incorrect_interval(schedule_day: ScheduleDay) -> None:
    """Test a schedule day with an incorrect interval."""
    for start, end in (("01:00", "00:30"), ("00:foo", "bar")):
        with pytest.raises(ValueError):
            schedule_day.set_state(STATE_ON, start, end)


def test_schedule_day_with_incorrect_state(schedule_day: ScheduleDay) -> None:
    """Test a schedule day with an incorrect state."""
    with pytest.raises(ValueError):
        schedule_day.set_state("invalid_state", "00:00", "01:00")  # type: ignore [arg-type]


def test_setting_whole_day_schedule(schedule_day: ScheduleDay) -> None:
    """Test setting schedule for a whole day."""
    schedule_day.set_on()
    assert schedule_day.intervals == [True for _ in range(48)]
    schedule_day.set_off()
    assert schedule_day.intervals == [False for _ in range(48)]


def test_setting_schedule_with_sequence(schedule_day: ScheduleDay) -> None:
    """Test setting a schedule via sequence methods."""
    schedule_day.set_on("00:30", "01:00")
    schedule_day_iter = iter(schedule_day)
    assert not next(schedule_day_iter)
    assert next(schedule_day_iter)
    assert schedule_day[1]
    schedule_day[1] = False
    del schedule_day[0]
    assert not schedule_day[0]
    schedule_day.append(True)
    assert schedule_day[-1]


def test_schedule_day_repr(schedule_day: ScheduleDay) -> None:
    """Test serializable representation of a schedule day."""
    assert repr(schedule_day) == f"ScheduleDay({[False for _ in range(48)]})"


def test_schedule(schedule: Schedule) -> None:
    """Test a schedule."""
    schedule_iter = iter(schedule)
    assert not next(schedule_iter)[0]
    assert next(schedule_iter)[0]


@patch("pyplumio.helpers.schedule.factory")
def test_schedule_commit(mock_factory, schedule: Schedule) -> None:
    """Test committing a schedule."""
    schedule.device = Mock(spec=Device)
    schedule.device.address = DeviceType.ECOMAX
    schedule.device.data = {
        f"test_{ATTR_SCHEDULE_SWITCH}": 1,
        f"test_{ATTR_SCHEDULE_PARAMETER}": 2,
        ATTR_SCHEDULES: {"test": schedule},
    }
    schedule.device.queue = Mock(spec=asyncio.Queue)

    schedule.commit()
    mock_factory.assert_called_once_with(
        "frames.requests.SetScheduleRequest",
        recipient=DeviceType.ECOMAX,
        data={
            ATTR_TYPE: "test",
            ATTR_SWITCH: 1,
            ATTR_PARAMETER: 2,
            ATTR_SCHEDULE: schedule,
        },
    )
