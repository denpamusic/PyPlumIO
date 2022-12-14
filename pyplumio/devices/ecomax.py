"""Contains ecoMAX device representation."""
from __future__ import annotations

import asyncio
from collections.abc import Sequence
import logging
import time
from typing import ClassVar, Final, Tuple

from pyplumio.const import (
    ATTR_ECOMAX_PARAMETERS,
    ATTR_ECOMAX_SENSORS,
    ATTR_FRAME_VERSIONS,
    ATTR_FUEL_BURNED,
    ATTR_FUEL_CONSUMPTION,
    ATTR_MIXER_PARAMETERS,
    ATTR_MIXER_SENSORS,
    ATTR_MIXERS,
    ATTR_PARAMETER,
    ATTR_PRODUCT,
    ATTR_REGDATA,
    ATTR_SCHEDULE,
    ATTR_SCHEDULES,
    ATTR_SCHEMA,
    ATTR_STATE,
    ATTR_SWITCH,
    DeviceState,
    DeviceType,
    FrameType,
)
from pyplumio.devices import Device, Mixer
from pyplumio.helpers.data_types import Boolean
from pyplumio.helpers.filters import on_change
from pyplumio.helpers.frame_versions import DEFAULT_FRAME_VERSION, FrameVersions
from pyplumio.helpers.parameter import (
    EcomaxBinaryParameter,
    EcomaxParameter,
    MixerBinaryParameter,
    MixerParameter,
    ScheduleBinaryParameter,
    ScheduleParameter,
    is_binary_parameter,
)
from pyplumio.helpers.product_info import ProductType
from pyplumio.helpers.schedule import Schedule, ScheduleDay
from pyplumio.helpers.typing import DeviceDataType, ParameterDataType, VersionsInfoType
from pyplumio.structures.ecomax_parameters import (
    ECOMAX_I_PARAMETERS,
    ECOMAX_P_PARAMETERS,
    PARAMETER_BOILER_CONTROL,
    PARAMETER_ECOMAX_CONTROL,
)
from pyplumio.structures.mixer_parameters import (
    ECOMAX_I_MIXER_PARAMETERS,
    ECOMAX_P_MIXER_PARAMETERS,
)

MAX_TIME_SINCE_LAST_FUEL_DATA: Final = 300

_LOGGER = logging.getLogger(__name__)


class EcoMAX(Device):
    """Represents ecoMAX controller."""

    address: ClassVar[int] = DeviceType.ECOMAX
    _frame_versions: FrameVersions
    _fuel_burned_timestamp: float = 0.0
    _required_frames: Sequence[int] = (
        FrameType.REQUEST_UID,
        FrameType.REQUEST_DATA_SCHEMA,
        FrameType.REQUEST_ECOMAX_PARAMETERS,
        FrameType.REQUEST_MIXER_PARAMETERS,
        FrameType.REQUEST_PASSWORD,
        FrameType.REQUEST_ALERTS,
        FrameType.REQUEST_SCHEDULES,
    )

    def __init__(self, queue: asyncio.Queue):
        """Initialize new ecoMAX object."""
        super().__init__(queue)
        self._frame_versions = FrameVersions(device=self)
        self._fuel_burned_timestamp = time.time()
        self.subscribe(ATTR_ECOMAX_SENSORS, self._add_ecomax_sensors)
        self.subscribe(ATTR_STATE, on_change(self._add_ecomax_control_parameter))
        self.subscribe(ATTR_FUEL_CONSUMPTION, self._add_burned_fuel_counter)
        self.subscribe(ATTR_ECOMAX_PARAMETERS, self._add_ecomax_parameters)
        self.subscribe(ATTR_REGDATA, self._decode_regulator_data)
        self.subscribe(ATTR_MIXER_SENSORS, self._add_mixer_sensors)
        self.subscribe(ATTR_MIXER_PARAMETERS, self._add_mixer_parameters)
        self.subscribe(ATTR_SCHEDULES, self._add_schedules_and_schedule_parameters)
        self.subscribe_once(ATTR_FRAME_VERSIONS, self._merge_required_frames)
        self.subscribe(ATTR_FRAME_VERSIONS, self._frame_versions.async_update)

    async def _merge_required_frames(
        self, frame_versions: VersionsInfoType
    ) -> VersionsInfoType:
        """Merge required frames into version list."""
        requirements = {int(x): DEFAULT_FRAME_VERSION for x in self.required_frames}
        return {**requirements, **frame_versions}

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

    async def _add_ecomax_sensors(self, sensors: DeviceDataType) -> bool:
        """Add ecomax sensor values to the device data."""
        for name, value in sensors.items():
            await self.async_set_device_data(name, value)

        return True

    async def _add_ecomax_parameters(
        self, parameters: Sequence[Tuple[int, ParameterDataType]]
    ) -> bool:
        """Add ecomax parameters to the device data."""
        product = await self.get_value(ATTR_PRODUCT)
        for ecomax_parameter in parameters:
            key, value = ecomax_parameter
            cls = (
                EcomaxBinaryParameter if is_binary_parameter(value) else EcomaxParameter
            )
            parameter = cls(
                device=self,
                name=(
                    ECOMAX_P_PARAMETERS[key]
                    if product.type == ProductType.ECOMAX_P
                    else ECOMAX_I_PARAMETERS[key]
                ),
                value=value[0],
                min_value=value[1],
                max_value=value[2],
            )
            await self.async_set_device_data(parameter.name, parameter)

        return True

    async def _add_mixer_sensors(self, sensors: Sequence[DeviceDataType]) -> bool:
        """Set sensor values for the mixer."""
        for mixer_number, mixer_data in enumerate(sensors):
            mixer = self._get_mixer(mixer_number, len(sensors))
            for name, value in mixer_data.items():
                await mixer.async_set_device_data(name, value)

        return True

    async def _add_mixer_parameters(
        self, parameters: Sequence[Sequence[Tuple[int, ParameterDataType]]]
    ) -> bool:
        """Set mixer parameters."""
        product = await self.get_value(ATTR_PRODUCT)
        for mixer_number, mixer_parameters in enumerate(parameters):
            mixer = self._get_mixer(mixer_number, len(parameters))
            for mixer_parameter in mixer_parameters:
                index, value = mixer_parameter
                cls = (
                    MixerBinaryParameter
                    if is_binary_parameter(value)
                    else MixerParameter
                )
                parameter = cls(
                    device=self,
                    name=(
                        ECOMAX_P_MIXER_PARAMETERS[index]
                        if product.type == ProductType.ECOMAX_P
                        else ECOMAX_I_MIXER_PARAMETERS[index]
                    ),
                    value=value[0],
                    min_value=value[1],
                    max_value=value[2],
                    extra=mixer_number,
                )
                await mixer.async_set_device_data(parameter.name, parameter)

        return True

    async def _add_ecomax_control_parameter(self, mode: int) -> None:
        """Add ecoMAX control parameter to the device instance."""
        parameter = EcomaxBinaryParameter(
            device=self,
            name=PARAMETER_ECOMAX_CONTROL,
            value=(mode != DeviceState.OFF),
            min_value=0,
            max_value=1,
        )
        await self.async_set_device_data(PARAMETER_ECOMAX_CONTROL, parameter)
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

    async def turn_on(self) -> bool:
        """Turn on the ecoMAX controller."""
        try:
            return await self.data[PARAMETER_ECOMAX_CONTROL].turn_on()
        except KeyError:
            _LOGGER.error("ecoMAX control is not available, please try later")
            return False

    async def turn_off(self) -> bool:
        """Turn off the ecoMAX controller."""
        try:
            return await self.data[PARAMETER_ECOMAX_CONTROL].turn_off()
        except KeyError:
            _LOGGER.error("ecoMAX control is not available, please try later")
            return False

    async def shutdown(self) -> None:
        """Cancel scheduled tasks."""
        mixers = self.data.get(ATTR_MIXERS, [])
        for mixer in mixers:
            await mixer.shutdown()

        await super().shutdown()

    @property
    def required_frames(self) -> Sequence[int]:
        """Return list of required frame types."""
        return self._required_frames
