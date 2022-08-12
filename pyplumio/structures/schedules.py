"""Contains schedule decoder."""

from typing import Final, List, Optional, Sequence, Tuple, Union

from pyplumio.const import (
    ATTR_PARAMETER,
    ATTR_SCHEDULE,
    ATTR_SCHEDULES,
    ATTR_SWITCH,
    ATTR_TYPE,
)
from pyplumio.exceptions import FrameDataError
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures import Structure, make_device_data
from pyplumio.util import unpack_parameter

SCHEDULE_SIZE: Final = 42  # 6 bytes per day, 7 days total

SCHEDULES: Tuple[str, ...] = (
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


def _split_byte(byte: int) -> List[bool]:
    """Split single byte into an eight bits."""
    bits = []
    for bit in reversed(range(8)):
        bits.append(bool(byte & (1 << bit)))

    return bits


def _join_byte(bits: Sequence[Union[int, bool]]) -> int:
    """Join eight bits into a single byte."""
    result = 0
    for bit in bits:
        result = (result << 1) | bit

    return result


def _decode_schedule(message: bytearray, offset: int) -> Tuple[List[List[bool]], int]:
    """Return schedule data and offset."""
    schedule: List[List[bool]] = []
    day: List[bool] = []

    last_offset = offset + SCHEDULE_SIZE
    while offset < last_offset:
        if len(day) == 48:
            schedule.append(day)
            day = []

        day.extend(_split_byte(message[offset]))
        offset += 1

    schedule.append(day)

    return schedule, offset


class SchedulesStructure(Structure):
    """Represents schedule data structure."""

    def encode(self, data: DeviceDataType) -> bytearray:
        """Encode device data to bytearray message."""
        message = bytearray()
        message.append(1)
        try:
            message.append(SCHEDULES.index(data[ATTR_TYPE]))
            message.append(int(data[ATTR_SWITCH]))
            message.append(int(data[ATTR_PARAMETER]))
            schedule = data[ATTR_SCHEDULE]
        except (KeyError, ValueError) as e:
            raise FrameDataError from e

        schedule_bytes = []
        for day in list(schedule):
            schedule_bytes += [
                _join_byte(day[i : i + 8]) for i in range(0, len(day), 8)
            ]

        message += bytearray(schedule_bytes)

        return message

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        first_block = message[offset + 1]
        block_number = message[offset + 2]
        offset += 3
        schedules = {}
        for _ in range(first_block, first_block + block_number):
            schedule_type = message[offset]
            schedule_name = SCHEDULES[schedule_type]
            schedule: DeviceDataType = {}
            schedule[ATTR_SWITCH] = (message[offset + 1], 0, 1)
            schedule[ATTR_PARAMETER] = unpack_parameter(message, offset + 2)
            schedule[ATTR_SCHEDULE], offset = _decode_schedule(message, offset + 5)
            schedules[schedule_name] = schedule

        return make_device_data(data, {ATTR_SCHEDULES: schedules}), offset
