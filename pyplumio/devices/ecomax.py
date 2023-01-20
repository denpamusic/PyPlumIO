"""Contains ecoMAX device representation."""
from __future__ import annotations

import asyncio
from collections.abc import Sequence
import logging
import time
from typing import ClassVar, Final, List, Optional, Tuple

from pyplumio.const import (
    ATTR_LOADED,
    ATTR_PASSWORD,
    ATTR_SENSORS,
    ATTR_STATE,
    STATE_OFF,
    STATE_ON,
    DeviceState,
    DeviceType,
    FrameType,
)
from pyplumio.devices import Addressable, Mixer, Thermostat
from pyplumio.frames import DataFrameDescription, get_frame_handler, is_known_frame_type
from pyplumio.helpers.factory import factory
from pyplumio.helpers.filters import on_change
from pyplumio.helpers.product_info import ProductType
from pyplumio.helpers.schedule import Schedule, ScheduleDay
from pyplumio.helpers.typing import DeviceDataType, ParameterDataType, VersionsInfoType
from pyplumio.structures import StructureDecoder
from pyplumio.structures.alerts import ATTR_ALERTS
from pyplumio.structures.data_schema import ATTR_SCHEMA
from pyplumio.structures.ecomax_parameters import (
    ATTR_ECOMAX_CONTROL,
    ATTR_ECOMAX_PARAMETERS,
    ECOMAX_CONTROL_PARAMETER,
    ECOMAX_I_PARAMETERS,
    ECOMAX_P_PARAMETERS,
    THERMOSTAT_PROFILE_PARAMETER,
    EcomaxParameter,
)
from pyplumio.structures.frame_versions import ATTR_FRAME_VERSIONS
from pyplumio.structures.fuel_consumption import ATTR_FUEL_CONSUMPTION
from pyplumio.structures.mixer_parameters import (
    ATTR_MIXER_PARAMETERS,
    ECOMAX_I_MIXER_PARAMETERS,
    ECOMAX_P_MIXER_PARAMETERS,
)
from pyplumio.structures.mixer_sensors import ATTR_MIXER_SENSORS
from pyplumio.structures.product_info import ATTR_PRODUCT
from pyplumio.structures.regulator_data import ATTR_REGDATA, ATTR_REGDATA_DECODER
from pyplumio.structures.schedules import (
    ATTR_SCHEDULE_PARAMETERS,
    ATTR_SCHEDULES,
    SCHEDULE_PARAMETERS,
    SCHEDULES,
)
from pyplumio.structures.thermostat_parameters import (
    ATTR_THERMOSTAT_PARAMETERS,
    ATTR_THERMOSTAT_PARAMETERS_DECODER,
    ATTR_THERMOSTAT_PROFILE,
    THERMOSTAT_PARAMETERS,
)
from pyplumio.structures.thermostat_sensors import ATTR_THERMOSTAT_SENSORS

ATTR_MIXERS: Final = "mixers"
ATTR_THERMOSTATS: Final = "thermostats"
ATTR_FUEL_BURNED: Final = "fuel_burned"

MAX_TIME_SINCE_LAST_FUEL_DATA: Final = 300

DATA_FRAME_TYPES: Tuple[DataFrameDescription, ...] = (
    DataFrameDescription(frame_type=FrameType.REQUEST_UID, provides=ATTR_PRODUCT),
    DataFrameDescription(
        frame_type=FrameType.REQUEST_DATA_SCHEMA, provides=ATTR_SCHEMA
    ),
    DataFrameDescription(
        frame_type=FrameType.REQUEST_ECOMAX_PARAMETERS, provides=ATTR_ECOMAX_PARAMETERS
    ),
    DataFrameDescription(frame_type=FrameType.REQUEST_ALERTS, provides=ATTR_ALERTS),
    DataFrameDescription(
        frame_type=FrameType.REQUEST_SCHEDULES, provides=ATTR_SCHEDULES
    ),
    DataFrameDescription(
        frame_type=FrameType.REQUEST_MIXER_PARAMETERS, provides=ATTR_MIXER_PARAMETERS
    ),
    DataFrameDescription(
        frame_type=FrameType.REQUEST_THERMOSTAT_PARAMETERS,
        provides=ATTR_THERMOSTAT_PARAMETERS,
    ),
    DataFrameDescription(frame_type=FrameType.REQUEST_PASSWORD, provides=ATTR_PASSWORD),
)

_LOGGER = logging.getLogger(__name__)


class EcoMAX(Addressable):
    """Represents ecoMAX controller."""

    address: ClassVar[int] = DeviceType.ECOMAX
    _frame_versions: VersionsInfoType
    _fuel_burned_timestamp: float = 0.0

    def __init__(self, queue: asyncio.Queue):
        """Initialize new ecoMAX object."""
        super().__init__(queue)
        self._frame_versions = {}
        self._fuel_burned_timestamp = time.time()
        self.subscribe(ATTR_SENSORS, self._add_ecomax_sensors)
        self.subscribe(ATTR_STATE, on_change(self._add_ecomax_control_parameter))
        self.subscribe(ATTR_FUEL_CONSUMPTION, self._add_burned_fuel_counter)
        self.subscribe(ATTR_ECOMAX_PARAMETERS, self._add_ecomax_parameters)
        self.subscribe(ATTR_REGDATA_DECODER, self._decode_regulator_data)
        self.subscribe(ATTR_MIXER_SENSORS, self._add_mixer_sensors)
        self.subscribe(ATTR_MIXER_PARAMETERS, self._add_mixer_parameters)
        self.subscribe(ATTR_SCHEDULES, self._add_schedules)
        self.subscribe(ATTR_SCHEDULE_PARAMETERS, self._add_schedule_parameters)
        self.subscribe(ATTR_FRAME_VERSIONS, self._update_frame_versions)
        self.subscribe(ATTR_THERMOSTAT_SENSORS, self._add_thermostat_sensors)
        self.subscribe(ATTR_THERMOSTAT_PROFILE, self._add_thermostat_profile_parameter)
        self.subscribe(ATTR_THERMOSTAT_PARAMETERS, self._add_thermostat_parameters)
        self.subscribe(
            ATTR_THERMOSTAT_PARAMETERS_DECODER, self._decode_thermostat_parameters
        )
        self.subscribe_once(ATTR_LOADED, self._request_data_frames)

    async def _request_data_frames(self, loaded: bool) -> None:
        """Request initial data frames."""
        try:
            await asyncio.gather(
                *{
                    self.create_task(
                        self.request_value(
                            description.provides, description.frame_type, timeout=5
                        )
                    )
                    for description in DATA_FRAME_TYPES
                }
            )
        except ValueError as e:
            _LOGGER.error("Request failed: %s", e)

    async def _update_frame_versions(self, versions: VersionsInfoType) -> None:
        """Check versions and fetch outdated frames."""
        for frame_type, version in versions.items():
            if is_known_frame_type(frame_type) and (
                frame_type not in self._frame_versions
                or self._frame_versions[frame_type] != version
            ):
                # We don't have this frame or it's version has changed.
                request = factory(get_frame_handler(frame_type), recipient=self.address)
                self.queue.put_nowait(request)
                self._frame_versions[frame_type] = version

    def _get_mixer(self, index: int, mixer_count: int) -> Mixer:
        """Get or create a new mixer object and add it to the device."""
        mixers = self.data.setdefault(ATTR_MIXERS, [])
        try:
            mixer = mixers[index]
        except IndexError:
            mixer = Mixer(self.queue, parent=self, index=index)
            mixers.append(mixer)
            if len(mixers) == mixer_count:
                # All mixers were processed, notify callbacks and getters.
                self.set_device_data(ATTR_MIXERS, mixers)

        return mixer

    def _get_thermostat(self, index: int, thermostat_count: int) -> Thermostat:
        """Get or create a new thermostat object and add it to the
        device."""
        thermostats = self.data.setdefault(ATTR_THERMOSTATS, [])
        try:
            thermostat = thermostats[index]
        except IndexError:
            thermostat = Thermostat(self.queue, parent=self, index=index)
            thermostats.append(thermostat)
            if len(thermostats) == thermostat_count:
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
        for index, value in parameters:
            description = (
                ECOMAX_P_PARAMETERS[index]
                if product.type == ProductType.ECOMAX_P
                else ECOMAX_I_PARAMETERS[index]
            )
            parameter = description.cls(
                device=self,
                description=description,
                index=index,
                value=value[0],
                min_value=value[1],
                max_value=value[2],
            )
            await self.async_set_device_data(description.name, parameter)

        return True

    async def _add_mixer_sensors(
        self, sensors: Sequence[Tuple[int, DeviceDataType]]
    ) -> bool:
        """Set sensor values for the mixer."""
        for mixer_index, mixer_sensors in sensors:
            mixer = self._get_mixer(mixer_index, len(sensors))
            for name, value in mixer_sensors.items():
                await mixer.async_set_device_data(name, value)

        return True

    async def _add_mixer_parameters(
        self,
        parameters: Optional[
            Sequence[Tuple[int, Sequence[Tuple[int, ParameterDataType]]]]
        ],
    ) -> bool:
        """Set mixer parameters."""
        if parameters is None:
            return False

        product = await self.get_value(ATTR_PRODUCT)
        for mixer_index, mixer_parameters in parameters:
            mixer = self._get_mixer(mixer_index, len(parameters))
            for index, value in mixer_parameters:
                description = (
                    ECOMAX_P_MIXER_PARAMETERS[index]
                    if product.type == ProductType.ECOMAX_P
                    else ECOMAX_I_MIXER_PARAMETERS[index]
                )
                parameter = description.cls(
                    device=mixer,
                    description=description,
                    index=index,
                    value=value[0],
                    min_value=value[1],
                    max_value=value[2],
                )
                await mixer.async_set_device_data(description.name, parameter)

        return True

    async def _add_thermostat_sensors(
        self, sensors: Sequence[Tuple[int, DeviceDataType]]
    ) -> bool:
        """Set sensor values for the thermostat."""
        for thermostat_index, thermostat_sensors in sensors:
            thermostat = self._get_thermostat(thermostat_index, len(sensors))
            for name, value in thermostat_sensors.items():
                await thermostat.async_set_device_data(name, value)

        return True

    async def _add_thermostat_parameters(
        self,
        parameters: Optional[
            Sequence[Tuple[int, Sequence[Tuple[int, ParameterDataType]]]]
        ],
    ) -> bool:
        """Set thermostat parameters."""
        if parameters is None:
            return False

        for thermostat_index, thermostat_parameters in parameters:
            thermostat = self._get_thermostat(thermostat_index, len(parameters))
            for index, value in thermostat_parameters:
                description = THERMOSTAT_PARAMETERS[index]
                parameter = description.cls(
                    device=thermostat,
                    description=description,
                    index=index,
                    value=value[0],
                    min_value=value[1],
                    max_value=value[2],
                    offset=(thermostat_index * len(thermostat_parameters)),
                )
                await thermostat.async_set_device_data(description.name, parameter)

        return True

    async def _add_thermostat_profile_parameter(
        self, parameter: ParameterDataType
    ) -> Optional[EcomaxParameter]:
        """Add thermostat profile parameter to the device instance."""
        if parameter is not None:
            return THERMOSTAT_PROFILE_PARAMETER.cls(
                device=self,
                description=THERMOSTAT_PROFILE_PARAMETER,
                value=parameter[0],
                min_value=parameter[1],
                max_value=parameter[2],
            )

        return None

    async def _decode_thermostat_parameters(self, decoder: StructureDecoder) -> bool:
        """Decode thermostat parameters."""
        data = decoder.decode(decoder.frame.message, data=self.data)[0]
        for field in (ATTR_THERMOSTAT_PROFILE, ATTR_THERMOSTAT_PARAMETERS):
            await self.async_set_device_data(field, data[field])

        return True

    async def _add_ecomax_control_parameter(self, mode: int) -> None:
        """Add ecoMAX control parameter to the device instance."""
        parameter = ECOMAX_CONTROL_PARAMETER.cls(
            device=self,
            description=ECOMAX_CONTROL_PARAMETER,
            value=(mode != DeviceState.OFF),
            min_value=STATE_OFF,
            max_value=STATE_ON,
        )
        await self.async_set_device_data(ECOMAX_CONTROL_PARAMETER.name, parameter)

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

    async def _add_schedule_parameters(
        self, parameters: Sequence[Tuple[int, ParameterDataType]]
    ) -> bool:
        for index, value in parameters:
            description = SCHEDULE_PARAMETERS[index]
            parameter = description.cls(
                device=self,
                description=description,
                index=index,
                value=value[0],
                min_value=value[1],
                max_value=value[2],
            )
            await self.async_set_device_data(description.name, parameter)

        return True

    async def _add_schedules(
        self, schedules: List[Tuple[int, List[List[bool]]]]
    ) -> DeviceDataType:
        """Add schedules."""
        return {
            SCHEDULES[index]: Schedule(
                name=SCHEDULES[index],
                device=self,
                monday=ScheduleDay(schedule[1]),
                tuesday=ScheduleDay(schedule[2]),
                wednesday=ScheduleDay(schedule[3]),
                thursday=ScheduleDay(schedule[4]),
                friday=ScheduleDay(schedule[5]),
                saturday=ScheduleDay(schedule[6]),
                sunday=ScheduleDay(schedule[0]),
            )
            for index, schedule in schedules
        }

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
