"""Contains an ecoMAX class."""
from __future__ import annotations

import asyncio
from collections.abc import Generator, Iterable, Sequence
import logging
import time
from typing import ClassVar, Final

from pyplumio.const import (
    ATTR_FRAME_ERRORS,
    ATTR_PASSWORD,
    ATTR_SENSORS,
    ATTR_STATE,
    STATE_OFF,
    STATE_ON,
    DeviceState,
    DeviceType,
    FrameType,
    ProductType,
)
from pyplumio.devices import Addressable
from pyplumio.devices.mixer import Mixer
from pyplumio.devices.thermostat import Thermostat
from pyplumio.filters import on_change
from pyplumio.frames import (
    DataFrameDescription,
    Frame,
    Request,
    get_frame_handler,
    is_known_frame_type,
)
from pyplumio.helpers.factory import factory
from pyplumio.helpers.schedule import Schedule, ScheduleDay
from pyplumio.helpers.typing import EventDataType, ParameterDataType
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
from pyplumio.structures.mixer_parameters import ATTR_MIXER_PARAMETERS
from pyplumio.structures.mixer_sensors import ATTR_MIXER_SENSORS
from pyplumio.structures.network_info import ATTR_NETWORK, NetworkInfo
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
)
from pyplumio.structures.thermostat_sensors import ATTR_THERMOSTAT_SENSORS

ATTR_MIXERS: Final = "mixers"
ATTR_THERMOSTATS: Final = "thermostats"
ATTR_FUEL_BURNED: Final = "fuel_burned"

MAX_TIME_SINCE_LAST_FUEL_UPDATE_NS: Final = 300 * 1000000000

DATA_FRAME_TYPES: tuple[DataFrameDescription, ...] = (
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
    """Represents an ecoMAX controller."""

    address: ClassVar[int] = DeviceType.ECOMAX
    _frame_versions: dict[int, int]
    _frame_types: tuple[DataFrameDescription, ...] = DATA_FRAME_TYPES
    _fuel_burned_timestamp_ns: int = 0

    def __init__(self, queue: asyncio.Queue, network: NetworkInfo):
        """Initialize a new ecoMAX controller."""
        super().__init__(queue, network)
        self._frame_versions = {}
        self._fuel_burned_timestamp_ns = time.perf_counter_ns()
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

    async def async_setup(self) -> bool:
        """Setup an ecoMAX controller."""
        await self.wait_for(ATTR_SENSORS)
        return await super().async_setup()

    def handle_frame(self, frame: Frame) -> None:
        """Handle frame received from the ecoMAX device."""
        if isinstance(frame, Request) and frame.frame_type in (
            FrameType.REQUEST_CHECK_DEVICE,
            FrameType.REQUEST_PROGRAM_VERSION,
        ):
            self.queue.put_nowait(frame.response(data={ATTR_NETWORK: self._network}))

        super().handle_frame(frame)

    def _has_frame_version(self, frame_type: FrameType | int, version: int) -> bool:
        """Check if ecoMAX controller has this version of the frame."""
        return (
            frame_type in self._frame_versions
            and self._frame_versions[frame_type] == version
        )

    def _frame_is_supported(self, frame_type: FrameType | int) -> bool:
        """Check if frame is supported by the device."""
        return frame_type not in self.data.get(ATTR_FRAME_ERRORS, [])

    async def _update_frame_versions(self, versions: dict[int, int]) -> None:
        """Check frame versions and update an outdated frames."""
        for frame_type, version in versions.items():
            if (
                is_known_frame_type(frame_type)
                and self._frame_is_supported(frame_type)
                and not self._has_frame_version(frame_type, version)
            ):
                # We don't have this frame or it's version has changed.
                request = factory(get_frame_handler(frame_type), recipient=self.address)
                self.queue.put_nowait(request)
                self._frame_versions[frame_type] = version

    def _mixers(self, indexes: Iterable[int]) -> Generator[Mixer, None, None]:
        """Iterate through the mixer indexes.

        For each index, return or create an instance of the mixer class.
        Once done, dispatch the 'mixers' event without waiting.
        """
        mixers = self.data.setdefault(ATTR_MIXERS, {})
        for index in indexes:
            if index not in mixers:
                mixers[index] = Mixer(self.queue, parent=self, index=index)

            yield mixers[index]

        return self.dispatch_nowait(ATTR_MIXERS, mixers)

    def _thermostats(self, indexes: Iterable[int]) -> Generator[Thermostat, None, None]:
        """Iterate through the thermostat indexes.

        For each index, return or create an instance of the thermostat
        class. Once done, dispatch the 'thermostats' event without
        waiting.
        """
        thermostats = self.data.setdefault(ATTR_THERMOSTATS, {})
        for index in indexes:
            if index not in thermostats:
                thermostats[index] = Thermostat(self.queue, parent=self, index=index)

            yield thermostats[index]

        return self.dispatch_nowait(ATTR_THERMOSTATS, thermostats)

    async def _add_ecomax_sensors(self, sensors: EventDataType) -> bool:
        """Handle ecoMAX sensors.

        For each sensor dispatch an event with the
        sensor's name and value.
        """
        for name, value in sensors.items():
            await self.dispatch(name, value)

        return True

    async def _add_ecomax_parameters(
        self, parameters: Sequence[tuple[int, ParameterDataType]]
    ) -> bool:
        """Handle ecoMAX parameters.

        For each parameter dispatch an event with the
        parameter's name and value.
        """
        product = await self.get(ATTR_PRODUCT)
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
            await self.dispatch(description.name, parameter)

        return True

    async def _add_mixer_sensors(self, sensors: dict[int, EventDataType]) -> bool:
        """Handle mixer sensors.

        For each sensor dispatch an event with the
        sensor's name and value. Events are dispatched for the
        respective mixer instance.
        """
        for mixer in self._mixers(sensors.keys()):
            await mixer.dispatch(ATTR_MIXER_SENSORS, sensors[mixer.index])

        return True

    async def _add_mixer_parameters(
        self,
        parameters: dict[int, Sequence[tuple[int, ParameterDataType]]] | None,
    ) -> bool:
        """Handle mixer parameters.

        For each parameter dispatch an event with the
        parameter's name and value. Events are dispatched for the
        respective mixer instance.
        """
        if parameters is None:
            return False

        for mixer in self._mixers(parameters.keys()):
            await mixer.dispatch(ATTR_MIXER_PARAMETERS, parameters[mixer.index])

        return True

    async def _add_thermostat_sensors(self, sensors: dict[int, EventDataType]) -> bool:
        """Handle thermostat sensors.

        For each sensor dispatch an event with the
        sensor's name and value. Events are dispatched for the
        respective thermostat instance.
        """
        for thermostat in self._thermostats(sensors.keys()):
            await thermostat.dispatch(
                ATTR_THERMOSTAT_SENSORS, sensors[thermostat.index]
            )

        return True

    async def _add_thermostat_parameters(
        self,
        parameters: dict[int, Sequence[tuple[int, ParameterDataType]]] | None,
    ) -> bool:
        """Handle thermostat parameters.

        For each parameter dispatch an event with the
        parameter's name and value. Events are dispatched for the
        respective thermostat instance.
        """
        if parameters is None:
            return False

        for thermostat in self._thermostats(parameters.keys()):
            await thermostat.dispatch(
                ATTR_THERMOSTAT_PARAMETERS, parameters[thermostat.index]
            )

        return True

    async def _add_thermostat_profile_parameter(
        self, parameter: ParameterDataType
    ) -> EcomaxParameter | None:
        """Add thermostat profile parameter to the dataset."""
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
        """Decode thermostat parameters.

        Dispatch 'thermostat_profile' and 'thermostat_parameters' event.
        """
        data = decoder.decode(decoder.frame.message, data=self.data)[0]
        for field in (ATTR_THERMOSTAT_PROFILE, ATTR_THERMOSTAT_PARAMETERS):
            await self.dispatch(field, data[field])

        return True

    async def _add_ecomax_control_parameter(self, mode: int) -> None:
        """Create ecoMAX control parameter instance and dispatch an
        'ecomax_control' event.
        """
        parameter = ECOMAX_CONTROL_PARAMETER.cls(
            device=self,
            description=ECOMAX_CONTROL_PARAMETER,
            value=(mode != DeviceState.OFF),
            min_value=STATE_OFF,
            max_value=STATE_ON,
        )
        await self.dispatch(ECOMAX_CONTROL_PARAMETER.name, parameter)

    async def _add_burned_fuel_counter(self, fuel_consumption: float) -> None:
        """Calculate fuel burned since last sensor's data message
        and dispatch 'fuel_burned' event.
        """
        current_timestamp_ns = time.perf_counter_ns()
        time_passed_ns = current_timestamp_ns - self._fuel_burned_timestamp_ns
        if time_passed_ns < MAX_TIME_SINCE_LAST_FUEL_UPDATE_NS:
            fuel_burned = fuel_consumption / (3600 * 1000000000) * time_passed_ns
            await self.dispatch(ATTR_FUEL_BURNED, fuel_burned)
        else:
            _LOGGER.warning(
                "Skipping outdated fuel consumption data, was %i seconds old",
                time_passed_ns / 1000000000,
            )

        self._fuel_burned_timestamp_ns = current_timestamp_ns

    async def _decode_regulator_data(self, decoder: StructureDecoder) -> bool:
        """Decode an ecoMAX regulator data.

        Dispatch 'frame_versions' and 'regdata' events.
        """
        data = decoder.decode(decoder.frame.message, data=self.data)[0]
        for field in (ATTR_FRAME_VERSIONS, ATTR_REGDATA):
            try:
                await self.dispatch(field, data[field])
            except KeyError:
                continue

        return True

    async def _add_schedule_parameters(
        self, parameters: Sequence[tuple[int, ParameterDataType]]
    ) -> bool:
        """Add schedule parameters to the dataset."""
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
            await self.dispatch(description.name, parameter)

        return True

    async def _add_schedules(
        self, schedules: list[tuple[int, list[list[bool]]]]
    ) -> EventDataType:
        """Add schedules to the dataset."""
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

    def turn_on_nowait(self) -> None:
        """Turn on the ecoMAX controller without waiting."""
        self.create_task(self.turn_on())

    def turn_off_nowait(self) -> None:
        """Turn off the ecoMAX controller without waiting."""
        self.create_task(self.turn_off())

    async def shutdown(self) -> None:
        """Shutdown tasks for the ecoMAX controller and sub-devices."""
        mixers = self.get_nowait(ATTR_MIXERS, {})
        thermostats = self.get_nowait(ATTR_THERMOSTATS, {})
        for subdevice in (mixers | thermostats).values():
            await subdevice.shutdown()

        try:
            await self.regdata.shutdown()
        except AttributeError:
            pass

        await super().shutdown()
