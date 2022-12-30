"""Contains ecoMAX device representation."""
from __future__ import annotations

import asyncio
from collections.abc import Sequence
import logging
import time
from typing import ClassVar, Final, Optional, Tuple

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
    ATTR_REGDATA_DECODER,
    ATTR_SCHEDULE,
    ATTR_SCHEDULES,
    ATTR_STATE,
    ATTR_SWITCH,
    ATTR_THERMOSTAT_PARAMETERS,
    ATTR_THERMOSTAT_PARAMETERS_DECODER,
    ATTR_THERMOSTAT_SENSORS,
    ATTR_THERMOSTATS,
    DeviceState,
    DeviceType,
    FrameType,
)
from pyplumio.devices import Device, Mixer, Thermostat
from pyplumio.helpers.filters import on_change
from pyplumio.helpers.frame_versions import DEFAULT_FRAME_VERSION, FrameVersions
from pyplumio.helpers.parameter import (
    EcomaxBinaryParameter,
    EcomaxParameter,
    MixerBinaryParameter,
    MixerParameter,
    ScheduleBinaryParameter,
    ScheduleParameter,
    ThermostatBinaryParameter,
    ThermostatParameter,
    is_binary_parameter,
)
from pyplumio.helpers.product_info import ProductType
from pyplumio.helpers.schedule import Schedule, ScheduleDay
from pyplumio.helpers.typing import DeviceDataType, ParameterDataType, VersionsInfoType
from pyplumio.structures import StructureDecoder
from pyplumio.structures.ecomax_parameters import (
    ATTR_BOILER_CONTROL,
    ATTR_ECOMAX_CONTROL,
    ECOMAX_I_PARAMETERS,
    ECOMAX_P_PARAMETERS,
)
from pyplumio.structures.mixer_parameters import (
    ECOMAX_I_MIXER_PARAMETERS,
    ECOMAX_P_MIXER_PARAMETERS,
)
from pyplumio.structures.thermostat_parameters import (
    ATTR_THERMOSTAT_PROFILE,
    THERMOSTAT_PARAMETERS,
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
        FrameType.REQUEST_THERMOSTAT_PARAMETERS,
    )

    def __init__(self, queue: asyncio.Queue):
        """Initialize new ecoMAX object."""
        super().__init__(queue)
        self._frame_versions = FrameVersions(device=self)
        self._fuel_burned_timestamp = time.time()
        self.subscribe_once(ATTR_FRAME_VERSIONS, self._merge_required_frames)
        self.subscribe(ATTR_ECOMAX_SENSORS, self._add_ecomax_sensors)
        self.subscribe(ATTR_STATE, on_change(self._add_ecomax_control_parameter))
        self.subscribe(ATTR_FUEL_CONSUMPTION, self._add_burned_fuel_counter)
        self.subscribe(ATTR_ECOMAX_PARAMETERS, self._add_ecomax_parameters)
        self.subscribe(ATTR_REGDATA_DECODER, self._decode_regulator_data)
        self.subscribe(ATTR_MIXER_SENSORS, self._add_mixer_sensors)
        self.subscribe(ATTR_MIXER_PARAMETERS, self._add_mixer_parameters)
        self.subscribe(ATTR_SCHEDULES, self._add_schedules_and_schedule_parameters)
        self.subscribe(ATTR_FRAME_VERSIONS, self._frame_versions.async_update)
        self.subscribe(ATTR_THERMOSTAT_SENSORS, self._add_thermostat_sensors)
        self.subscribe(ATTR_THERMOSTAT_PROFILE, self._add_thermostat_profile_parameter)
        self.subscribe(ATTR_THERMOSTAT_PARAMETERS, self._add_thermostat_parameters)
        self.subscribe(
            ATTR_THERMOSTAT_PARAMETERS_DECODER, self._decode_thermostat_parameters
        )

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

    def _get_thermostat(
        self, thermostat_number: int, total_thermostats: int
    ) -> Thermostat:
        """Get or create a new thermostat object and add it to the
        device."""
        thermostats = self.data.setdefault(ATTR_THERMOSTATS, [])
        try:
            thermostat = thermostats[thermostat_number]
        except IndexError:
            thermostat = Thermostat(thermostat_number)
            thermostats.append(thermostat)
            if len(thermostats) == total_thermostats:
                # All thermostats were processed, notify callbacks and getters.
                self.set_device_data(ATTR_THERMOSTATS, thermostats)

        return thermostat

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

    async def _add_mixer_sensors(
        self, sensors: Sequence[Tuple[int, DeviceDataType]]
    ) -> bool:
        """Set sensor values for the mixer."""
        for mixer_number, mixer_sensors in sensors:
            mixer = self._get_mixer(mixer_number, len(sensors))
            for name, value in mixer_sensors.items():
                await mixer.async_set_device_data(name, value)

        return True

    async def _add_mixer_parameters(
        self, parameters: Sequence[Tuple[int, Sequence[Tuple[int, ParameterDataType]]]]
    ) -> bool:
        """Set mixer parameters."""
        product = await self.get_value(ATTR_PRODUCT)
        for mixer_number, mixer_parameters in parameters:
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

    async def _add_thermostat_sensors(
        self, sensors: Sequence[Tuple[int, DeviceDataType]]
    ) -> bool:
        """Set sensor values for the thermostat."""
        for thermostat_number, thermostat_sensors in sensors:
            thermostat = self._get_thermostat(thermostat_number, len(sensors))
            for name, value in thermostat_sensors.items():
                await thermostat.async_set_device_data(name, value)

        return True

    async def _add_thermostat_parameters(
        self, parameters: Sequence[Tuple[int, Sequence[Tuple[int, ParameterDataType]]]]
    ) -> bool:
        """Set thermostat parameters."""
        for thermostat_number, thermostat_parameters in parameters:
            thermostat = self._get_thermostat(thermostat_number, len(parameters))
            for thermostat_parameter in thermostat_parameters:
                index, value = thermostat_parameter
                cls = (
                    ThermostatBinaryParameter
                    if is_binary_parameter(value)
                    else ThermostatParameter
                )
                parameter = cls(
                    device=self,
                    name=THERMOSTAT_PARAMETERS[index],
                    value=value[0],
                    min_value=value[1],
                    max_value=value[2],
                    extra=(thermostat_number * len(thermostat_parameters)),
                )
                await thermostat.async_set_device_data(parameter.name, parameter)

        return True

    async def _add_thermostat_profile_parameter(
        self, parameter: ParameterDataType
    ) -> Optional[EcomaxParameter]:
        """Add thermostat profile parameter to the device instance."""
        if parameter is not None:
            return EcomaxParameter(
                device=self,
                name=ATTR_THERMOSTAT_PROFILE,
                value=parameter[0],
                min_value=parameter[1],
                max_value=parameter[2],
            )

        return None

    async def _decode_thermostat_parameters(self, decoder: StructureDecoder) -> bool:
        """Decode thermostat parameters."""
        data = decoder.decode(decoder.frame.message, data=self.data)[0]
        for field in (ATTR_THERMOSTAT_PROFILE, ATTR_THERMOSTAT_PARAMETERS):
            try:
                await self.async_set_device_data(field, data[field])
            except KeyError:
                continue

        return True

    async def _add_ecomax_control_parameter(self, mode: int) -> None:
        """Add ecoMAX control parameter to the device instance."""
        parameter = EcomaxBinaryParameter(
            device=self,
            name=ATTR_ECOMAX_CONTROL,
            value=(mode != DeviceState.OFF),
            min_value=0,
            max_value=1,
        )
        await self.async_set_device_data(ATTR_ECOMAX_CONTROL, parameter)
        await self.async_set_device_data(ATTR_BOILER_CONTROL, parameter)

    async def _add_burned_fuel_counter(self, fuel_consumption: float) -> None:
        """Add burned fuel counter."""
        current_timestamp = time.time()
        seconds_passed = current_timestamp - self._fuel_burned_timestamp
        if 0 <= seconds_passed < MAX_TIME_SINCE_LAST_FUEL_DATA:
            fuel_burned = (fuel_consumption / 3600) * seconds_passed
            await self.async_set_device_data(ATTR_FUEL_BURNED, fuel_burned)
        else:
            _LOGGER.warning(
                "Skipping outdated fuel consumption data, was %i seconds old",
                seconds_passed,
            )

        self._fuel_burned_timestamp = current_timestamp

    async def _decode_regulator_data(self, decoder: StructureDecoder) -> bool:
        """Decode regulator data."""
        data = decoder.decode(decoder.frame.message, data=self.data)[0]
        for field in (ATTR_FRAME_VERSIONS, ATTR_REGDATA):
            try:
                await self.async_set_device_data(field, data[field])
            except KeyError:
                continue

        return True

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
            return await self.data[ATTR_ECOMAX_CONTROL].turn_on()
        except KeyError:
            _LOGGER.error("ecoMAX control is not available, please try later")
            return False

    async def turn_off(self) -> bool:
        """Turn off the ecoMAX controller."""
        try:
            return await self.data[ATTR_ECOMAX_CONTROL].turn_off()
        except KeyError:
            _LOGGER.error("ecoMAX control is not available, please try later")
            return False

    async def shutdown(self) -> None:
        """Cancel scheduled tasks for root and sub devices."""
        subdevices = []
        subdevices.extend(self.data.get(ATTR_MIXERS, []))
        subdevices.extend(self.data.get(ATTR_THERMOSTATS, []))
        for subdevice in subdevices:
            await subdevice.shutdown()

        await super().shutdown()

    @property
    def required_frames(self) -> Sequence[int]:
        """Return list of required frame types."""
        return self._required_frames
