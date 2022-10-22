"""Contains ecoMAX device representation."""
from __future__ import annotations

import asyncio
from collections.abc import Sequence
import time
from typing import ClassVar, Final, List

from pyplumio.const import (
    ATTR_BOILER_PARAMETERS,
    ATTR_BOILER_SENSORS,
    ATTR_FUEL_BURNED,
    ATTR_FUEL_CONSUMPTION,
    ATTR_MIXER_PARAMETERS,
    ATTR_MIXER_SENSORS,
    ATTR_MIXERS,
    ATTR_MODE,
    ATTR_PARAMETER,
    ATTR_REGDATA,
    ATTR_SCHEDULE,
    ATTR_SCHEDULES,
    ATTR_SCHEMA,
    ATTR_SWITCH,
)
from pyplumio.devices import Device, DeviceTypes, Mixer
from pyplumio.frames import FrameTypes
from pyplumio.helpers.data_types import Boolean
from pyplumio.helpers.filters import on_change
from pyplumio.helpers.parameter import (
    BoilerBinaryParameter,
    BoilerParameter,
    MixerBinaryParameter,
    MixerParameter,
    ScheduleBinaryParameter,
    ScheduleParameter,
    is_binary_parameter,
)
from pyplumio.helpers.schedule import Schedule, ScheduleDay
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures.boiler_parameters import PARAMETER_BOILER_CONTROL

MAX_TIME_SINCE_LAST_FUEL_DATA: Final = 300


class EcoMAX(Device):
    """Represents ecoMAX controller."""

    address: ClassVar[int] = DeviceTypes.ECOMAX
    _fuel_burned_timestamp: float = 0.0
    _required_frames: List[int] = [
        FrameTypes.REQUEST_UID,
        FrameTypes.REQUEST_DATA_SCHEMA,
        FrameTypes.REQUEST_BOILER_PARAMETERS,
        FrameTypes.REQUEST_MIXER_PARAMETERS,
        FrameTypes.REQUEST_PASSWORD,
        FrameTypes.REQUEST_ALERTS,
        FrameTypes.REQUEST_SCHEDULES,
    ]

    def __init__(self, queue: asyncio.Queue):
        """Initialize new ecoMAX object."""
        super().__init__(queue)
        self._fuel_burned_timestamp = time.time()
        self.subscribe(ATTR_BOILER_SENSORS, self._add_boiler_sensors)
        self.subscribe(ATTR_MODE, on_change(self._add_boiler_control_parameter))
        self.subscribe(ATTR_FUEL_CONSUMPTION, self._add_burned_fuel_counter)
        self.subscribe(ATTR_BOILER_PARAMETERS, self._add_boiler_parameters)
        self.subscribe(ATTR_REGDATA, self._decode_regulator_data)
        self.subscribe(ATTR_MIXER_SENSORS, self._set_mixer_sensors)
        self.subscribe(ATTR_MIXER_PARAMETERS, self._set_mixer_parameters)
        self.subscribe(ATTR_SCHEDULES, self._add_schedules_and_schedule_parameters)

    def _get_mixer(self, mixer_number: int, total_mixers: int) -> Mixer:
        """Get or create a new mixer object and add it to the device."""
        mixers = self.data.setdefault(ATTR_MIXERS, [])
        try:
            mixer = mixers[mixer_number]
        except IndexError:
            mixer = Mixer(mixer_number)
            mixers.append(mixer)
            if len(mixers) == total_mixers:
                # All mixers were processed, notify callbacks and getters.
                self.set_device_data(ATTR_MIXERS, mixers)

        return mixer

    async def _add_boiler_sensors(self, sensors: DeviceDataType) -> bool:
        """Add boiler sensors values to the device data."""
        for name, value in sensors.items():
            await self.async_set_device_data(name, value)

        return True

    async def _add_boiler_parameters(self, parameters: DeviceDataType) -> bool:
        """Add Parameter objects to the device data."""
        for name, value in parameters.items():
            cls = (
                BoilerBinaryParameter if is_binary_parameter(value) else BoilerParameter
            )
            parameter = cls(
                device=self,
                name=name,
                value=value[0],
                min_value=value[1],
                max_value=value[2],
            )
            await self.async_set_device_data(name, parameter)

        return True

    async def _set_mixer_sensors(self, sensors: Sequence[DeviceDataType]) -> bool:
        """Set sensor values for the mixer."""
        for mixer_number, mixer_data in enumerate(sensors):
            mixer = self._get_mixer(mixer_number, len(sensors))
            for name, value in mixer_data.items():
                await mixer.async_set_device_data(name, value)

        return True

    async def _set_mixer_parameters(self, parameters: Sequence[DeviceDataType]) -> bool:
        """Set mixer parameters."""
        for mixer_number, mixer_data in enumerate(parameters):
            mixer = self._get_mixer(mixer_number, len(parameters))
            for name, value in mixer_data.items():
                cls = (
                    MixerBinaryParameter
                    if is_binary_parameter(value)
                    else MixerParameter
                )
                parameter = cls(
                    device=self,
                    name=name,
                    value=value[0],
                    min_value=value[1],
                    max_value=value[2],
                    extra=mixer_number,
                )
                await mixer.async_set_device_data(name, parameter)

        return True

    async def _add_boiler_control_parameter(self, mode: int) -> None:
        """Add BoilerControl parameter to the device instance."""
        parameter = BoilerBinaryParameter(
            device=self,
            name=PARAMETER_BOILER_CONTROL,
            value=(mode != 0),
            min_value=0,
            max_value=1,
        )
        await self.async_set_device_data(PARAMETER_BOILER_CONTROL, parameter)

    async def _add_burned_fuel_counter(self, fuel_consumption: int) -> None:
        """Add burned fuel counter."""
        current_timestamp = time.time()
        seconds_passed = current_timestamp - self._fuel_burned_timestamp
        if 0 <= seconds_passed < MAX_TIME_SINCE_LAST_FUEL_DATA:
            fuel_burned = (fuel_consumption / 3600) * seconds_passed
            await self.async_set_device_data(ATTR_FUEL_BURNED, fuel_burned)

        self._fuel_burned_timestamp = current_timestamp

    async def _decode_regulator_data(self, regulator_data: bytes) -> DeviceDataType:
        """Add sensor values from the regulator data."""
        offset = 0
        boolean_index = 0
        regdata: DeviceDataType = {}
        schema = self.data.get(ATTR_SCHEMA, [])
        for parameter in schema:
            parameter_id, parameter_type = parameter
            if not isinstance(parameter_type, Boolean) and boolean_index > 0:
                offset += 1
                boolean_index = 0

            parameter_type.unpack(regulator_data[offset:])
            if isinstance(parameter_type, Boolean):
                boolean_index = parameter_type.index(boolean_index)

            regdata[parameter_id] = parameter_type.value
            offset += parameter_type.size

        return regdata

    async def _add_schedules_and_schedule_parameters(
        self, schedules: DeviceDataType
    ) -> DeviceDataType:
        """Add schedules and schedule parameters."""
        data: DeviceDataType = {}
        for name, schedule in schedules.items():
            for field in (ATTR_SWITCH, ATTR_PARAMETER):
                key = f"{ATTR_SCHEDULE}_{name}_{field}"
                value = schedule[field]
                cls = (
                    ScheduleBinaryParameter
                    if is_binary_parameter(value)
                    else ScheduleParameter
                )
                parameter = cls(
                    device=self,
                    name=key,
                    value=value[0],
                    min_value=value[1],
                    max_value=value[2],
                    extra=name,
                )
                await self.async_set_device_data(key, parameter)

            data[name] = Schedule(
                name=name,
                device=self,
                monday=ScheduleDay(schedule[ATTR_SCHEDULE][1]),
                tuesday=ScheduleDay(schedule[ATTR_SCHEDULE][2]),
                wednesday=ScheduleDay(schedule[ATTR_SCHEDULE][3]),
                thursday=ScheduleDay(schedule[ATTR_SCHEDULE][4]),
                friday=ScheduleDay(schedule[ATTR_SCHEDULE][5]),
                saturday=ScheduleDay(schedule[ATTR_SCHEDULE][6]),
                sunday=ScheduleDay(schedule[ATTR_SCHEDULE][0]),
            )

        return data

    async def shutdown(self) -> None:
        """Cancel scheduled tasks."""
        mixers = self.data.get(ATTR_MIXERS, [])
        for mixer in mixers:
            await mixer.shutdown()

        await super().shutdown()
