"""Contains test for schedule helpers."""


import asyncio
from unittest.mock import Mock, patch

import pytest

from pyplumio.const import (
    ATTR_PARAMETER,
    ATTR_SCHEDULE,
    ATTR_SCHEDULES,
    ATTR_SWITCH,
    ATTR_TYPE,
)
from pyplumio.devices import Device, DeviceTypes
from pyplumio.helpers.schedule import Schedule, ScheduleDay


@pytest.fixture(name="schedule_day")
def fixture_schedule_day() -> ScheduleDay:
    """Return instance of schedule day."""
    return ScheduleDay([False for _ in range(48)])


@pytest.fixture(name="schedule")
def fixture_schedule(schedule_day: ScheduleDay) -> Schedule:
    """Return instance of schedule."""
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
    """Test schedule day."""
    schedule_day.set_state("on", "00:00", "01:00")
    assert schedule_day.intervals[0]
    assert schedule_day.intervals[1]
    assert len(schedule_day) == 48

    # Test with incorrect interval.
    for (start, end) in (("01:00", "00:30"), ("00:foo", "bar")):
        with pytest.raises(ValueError):
            schedule_day.set_state("on", start, end)

    # Set whole day schedule.
    schedule_day.set_on()
    assert schedule_day.intervals == [True for _ in range(48)]
    schedule_day.set_off("00:30", "01:00")

    # Test sequence and iterable methods.
    schedule_day_iter = iter(schedule_day)
    assert next(schedule_day_iter)
    assert not next(schedule_day_iter)
    assert not schedule_day[1]
    schedule_day[1] = True
    del schedule_day[0]
    assert schedule_day[0]
    schedule_day.append(False)
    assert not schedule_day[-1]


def test_schedule_day_repr(schedule_day: ScheduleDay) -> None:
    """Test serializable representation of schedule day."""
    assert repr(schedule_day) == f"ScheduleDay({[False for _ in range(48)]})"


def test_schedule(schedule: Schedule) -> None:
    """Test schedule."""
    schedule_iter = iter(schedule)
    assert not next(schedule_iter)[0]
    assert next(schedule_iter)[0]


@patch("pyplumio.helpers.schedule.factory")
def test_schedule_commit(mock_factory, schedule: Schedule) -> None:
    """Test schedule commit."""
    schedule.device = Mock(spec=Device)
    schedule.device.address = DeviceTypes.ECOMAX
    schedule.device.data = {
        f"schedule_test_{ATTR_SWITCH}": 1,
        f"schedule_test_{ATTR_PARAMETER}": 2,
        ATTR_SCHEDULES: {"test": schedule},
    }
    schedule.device.queue = Mock(spec=asyncio.Queue)

    schedule.commit()
    mock_factory.assert_called_once_with(
        "frames.requests.SetScheduleRequest",
        recipient=DeviceTypes.ECOMAX,
        data={
            ATTR_TYPE: "test",
            ATTR_SWITCH: 1,
            ATTR_PARAMETER: 2,
            ATTR_SCHEDULE: schedule,
        },
    )
