"""Contains schedule decoder."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from functools import reduce
from itertools import chain
from typing import Final

from pyplumio.const import ATTR_PARAMETER, ATTR_SCHEDULE, ATTR_SWITCH, ATTR_TYPE
from pyplumio.devices import AddressableDevice, Device
from pyplumio.exceptions import FrameDataError
from pyplumio.frames import Request
from pyplumio.helpers.factory import factory
from pyplumio.helpers.parameter import (
    BinaryParameter,
    BinaryParameterDescription,
    Parameter,
    ParameterDescription,
    ParameterValues,
    unpack_parameter,
)
from pyplumio.helpers.typing import EventDataType
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


class ScheduleParameter(Parameter):
    """Represents a schedule parameter."""

    __slots__ = ()

    device: AddressableDevice

    @property
    def request(self) -> Request:
        """A request to change the parameter."""
        schedule_name, _ = self.description.name.split("_", 1)
        return factory(
            "frames.requests.SetScheduleRequest",
            recipient=self.device.address,
            data=collect_schedule_data(schedule_name, self.device),
        )


class ScheduleBinaryParameter(ScheduleParameter, BinaryParameter):
    """Represents a schedule binary parameter."""


@dataclass
class ScheduleParameterDescription(ParameterDescription):
    """Represents a schedule parameter description."""


@dataclass
class ScheduleBinaryParameterDescription(
    BinaryParameterDescription, ScheduleParameterDescription
):
    """Represents a schedule binary parameter description."""


SCHEDULE_PARAMETERS: list[ScheduleParameterDescription] = list(
    chain.from_iterable(
        [
            [
                ScheduleBinaryParameterDescription(
                    name=f"{name}_{ATTR_SCHEDULE_SWITCH}"
                ),
                ScheduleParameterDescription(name=f"{name}_{ATTR_SCHEDULE_PARAMETER}"),
            ]
            for name in SCHEDULES
        ]
    )
)


def collect_schedule_data(name: str, device: Device) -> EventDataType:
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
    return reduce(lambda x, y: (x << 1) | y, bits)


class SchedulesStructure(Structure):
    """Represents a schedule data structure."""

    _offset: int

    def encode(self, data: EventDataType) -> bytearray:
        """Encode data to the bytearray message."""
        message = bytearray([1])
        try:
            message.append(SCHEDULES.index(data[ATTR_TYPE]))
            message.append(int(data[ATTR_SWITCH]))
            message.append(int(data[ATTR_PARAMETER]))
            schedule = data[ATTR_SCHEDULE]
        except (KeyError, ValueError) as e:
            raise FrameDataError from e

        return message + bytearray(
            chain.from_iterable(
                [_join_bits(day[i : i + 8]) for i in range(0, len(day), 8)]
                for day in list(schedule)
            )
        )

    def _unpack_schedule(self, message: bytearray) -> list[list[bool]]:
        """Unpack a schedule."""
        schedule: list[bool] = []
        last_offset = self._offset + SCHEDULE_SIZE
        while self._offset < last_offset:
            schedule += _split_byte(message[self._offset])
            self._offset += 1

        # Split schedule. Each day consists of 48 half-hour intervals.
        return [schedule[i : i + 48] for i in range(0, len(schedule), 48)]

    def decode(
        self, message: bytearray, offset: int = 0, data: EventDataType | None = None
    ) -> tuple[EventDataType, int]:
        """Decode bytes and return message data and offset."""
        start = message[offset + 1]
        end = message[offset + 2]
        self._offset = offset + 3
        schedules: list[tuple[int, list[list[bool]]]] = []
        parameters: list[tuple[int, ParameterValues]] = []

        for _ in range(start, start + end):
            index = message[self._offset]
            switch = ParameterValues(
                value=message[self._offset + 1], min_value=0, max_value=1
            )
            parameter = unpack_parameter(message, self._offset + 2)
            self._offset += 5
            schedules.append((index, self._unpack_schedule(message)))
            parameters.append((index * 2, switch))
            parameters.append((index * 2 + 1, parameter))

        return (
            ensure_dict(
                data, {ATTR_SCHEDULES: schedules, ATTR_SCHEDULE_PARAMETERS: parameters}
            ),
            self._offset,
        )
