"""Contains schedule decoder."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from functools import reduce
from typing import Any, Final

from dataslots import dataslots

from pyplumio.const import (
    ATTR_PARAMETER,
    ATTR_SCHEDULE,
    ATTR_SWITCH,
    ATTR_TYPE,
    FrameType,
)
from pyplumio.devices import Device, PhysicalDevice
from pyplumio.exceptions import FrameDataError
from pyplumio.frames import Request
from pyplumio.helpers.parameter import (
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

    __slots__ = ()


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


@dataslots
@dataclass
class ScheduleNumberDescription(ScheduleParameterDescription, NumberDescription):
    """Represents a schedule number description."""


class ScheduleNumber(ScheduleParameter, Number):
    """Represents a schedule number."""

    __slots__ = ()

    description: ScheduleNumberDescription


@dataslots
@dataclass
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
