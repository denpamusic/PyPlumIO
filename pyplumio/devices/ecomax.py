"""Contains an ecoMAX class."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine, Generator, Iterable
import logging
import time
from typing import Any, Final, NamedTuple

from pyplumio.const import (
    ATTR_FRAME_ERRORS,
    ATTR_PASSWORD,
    ATTR_SENSORS,
    ATTR_SETUP,
    STATE_OFF,
    STATE_ON,
    DeviceState,
    DeviceType,
    FrameType,
    State,
)
from pyplumio.devices import PhysicalDevice, device_handler
from pyplumio.devices.mixer import Mixer
from pyplumio.devices.thermostat import Thermostat
from pyplumio.exceptions import RequestError
from pyplumio.filters import on_change
from pyplumio.frames import Frame, Request
from pyplumio.helpers.event_manager import event_listener
from pyplumio.parameters import ParameterValues
from pyplumio.parameters.ecomax import (
    ECOMAX_CONTROL_PARAMETER,
    THERMOSTAT_PROFILE_PARAMETER,
    EcomaxNumber,
    EcomaxSwitch,
    EcomaxSwitchDescription,
    get_ecomax_parameter_types,
)
from pyplumio.structures.alerts import ATTR_TOTAL_ALERTS
from pyplumio.structures.ecomax_parameters import (
    ATTR_ECOMAX_CONTROL,
    ATTR_ECOMAX_PARAMETERS,
)
from pyplumio.structures.mixer_parameters import ATTR_MIXER_PARAMETERS
from pyplumio.structures.network_info import ATTR_NETWORK_INFO, NetworkInfo
from pyplumio.structures.product_info import ATTR_PRODUCT, ProductInfo
from pyplumio.structures.regulator_data_schema import ATTR_REGDATA_SCHEMA
from pyplumio.structures.schedules import (
    ATTR_SCHEDULES,
    SCHEDULE_PARAMETERS,
    SCHEDULES,
    Schedule,
    ScheduleDay,
    ScheduleNumber,
    ScheduleSwitch,
    ScheduleSwitchDescription,
)
from pyplumio.structures.sensor_data import ATTR_MIXER_SENSORS, ATTR_THERMOSTAT_SENSORS
from pyplumio.structures.thermostat_parameters import ATTR_THERMOSTAT_PARAMETERS

_LOGGER = logging.getLogger(__name__)


ATTR_MIXERS: Final = "mixers"
ATTR_THERMOSTATS: Final = "thermostats"
ATTR_FUEL_BURNED: Final = "fuel_burned"

MAX_TIME_SINCE_LAST_FUEL_UPDATE: Final = 5 * 60


class FuelMeter:
    """Represents a fuel meter.

    Calculates the fuel burned based on the time
    elapsed since the last sensor message, which contains fuel
    consumption data. If the elapsed time is within the acceptable
    range, it returns the fuel burned data. Otherwise, it logs a
    warning and returns None.
    """

    __slots__ = ("_last_update_time",)

    _last_update_time: float

    def __init__(self) -> None:
        """Initialize a new fuel meter."""
        self._last_update_time = time.monotonic()

    def calculate(self, fuel_consumption: float) -> float | None:
        """Calculate the amount of burned fuel since last update."""
        current_time = time.monotonic()
        time_since_update = current_time - self._last_update_time
        self._last_update_time = current_time
        if time_since_update < MAX_TIME_SINCE_LAST_FUEL_UPDATE:
            return fuel_consumption * (time_since_update / 3600)

        _LOGGER.warning(
            "Skipping outdated fuel consumption data (was %f seconds old)",
            time_since_update,
        )
        return None


class DataKey(NamedTuple):
    """Map a data key to frame type."""

    key: str
    provided_by: FrameType


REQUIRED_KEYS: tuple[DataKey, ...] = (
    DataKey(ATTR_PRODUCT, FrameType.REQUEST_UID),
    DataKey(ATTR_REGDATA_SCHEMA, FrameType.REQUEST_REGULATOR_DATA_SCHEMA),
    DataKey(ATTR_ECOMAX_PARAMETERS, FrameType.REQUEST_ECOMAX_PARAMETERS),
    DataKey(ATTR_TOTAL_ALERTS, FrameType.REQUEST_ALERTS),
    DataKey(ATTR_SCHEDULES, FrameType.REQUEST_SCHEDULES),
    DataKey(ATTR_MIXER_PARAMETERS, FrameType.REQUEST_MIXER_PARAMETERS),
    DataKey(ATTR_THERMOSTAT_PARAMETERS, FrameType.REQUEST_THERMOSTAT_PARAMETERS),
    DataKey(ATTR_PASSWORD, FrameType.REQUEST_PASSWORD),
)

REQUIRED_TYPES = [frame_type for _, frame_type in REQUIRED_KEYS]

WAIT_FOR_SETUP_SECONDS: Final = 60.0


@device_handler(DeviceType.ECOMAX)
class EcoMAX(PhysicalDevice):
    """Represents an ecoMAX controller."""

    __slots__ = ("_fuel_meter",)

    _fuel_meter: FuelMeter

    def __init__(
        self, write_queue: asyncio.Queue[Frame], network_info: NetworkInfo
    ) -> None:
        """Initialize a new ecoMAX controller."""
        super().__init__(write_queue, network_info)
        self._fuel_meter = FuelMeter()

    def handle_frame(self, frame: Frame) -> None:
        """Handle frame received from the ecoMAX device."""
        if isinstance(frame, Request) and (
            response := frame.response(data={ATTR_NETWORK_INFO: self._network_info})
        ):
            self.queue_send(response)

        super().handle_frame(frame)

    def _mixers(self, indexes: Iterable[int]) -> Generator[Mixer]:
        """Iterate through indexes and yield a Mixer instance.

        For each index, return or create an instance of the mixer class.
        Once done, dispatch the 'mixers' event without waiting.
        """
        mixers: dict[int, Mixer] = self._data.setdefault(ATTR_MIXERS, {})
        for index in indexes:
            yield mixers.setdefault(
                index, Mixer(self._write_queue, parent=self, index=index)
            )

        return self.dispatch_nowait(ATTR_MIXERS, mixers)

    def _thermostats(self, indexes: Iterable[int]) -> Generator[Thermostat]:
        """Iterate through indexes and yield a Thermostat instance.

        For each index, return or create an instance of the thermostat
        class. Once done, dispatch the 'thermostats' event without
        waiting.
        """
        thermostats: dict[int, Thermostat] = self._data.setdefault(ATTR_THERMOSTATS, {})
        for index in indexes:
            yield thermostats.setdefault(
                index, Thermostat(self._write_queue, parent=self, index=index)
            )

        return self.dispatch_nowait(ATTR_THERMOSTATS, thermostats)

    async def _request_frame_version(
        self, frame_type: FrameType | int, version: int
    ) -> None:
        """Request frame version from the device."""
        setup_done = self.get_nowait(ATTR_SETUP, False)
        if setup_done or frame_type not in REQUIRED_TYPES:
            await super()._request_frame_version(frame_type, version)

    async def _set_ecomax_state(self, state: State) -> bool:
        """Try to set the ecoMAX control state."""
        try:
            return await self.set(ATTR_ECOMAX_CONTROL, state, timeout=0.0)
        except asyncio.TimeoutError:
            _LOGGER.error("ecoMAX control is not available. Please try again later.")

        return False

    async def turn_on(self) -> bool:
        """Turn on the ecoMAX controller."""
        return await self._set_ecomax_state(STATE_ON)

    async def turn_off(self) -> bool:
        """Turn off the ecoMAX controller."""
        return await self._set_ecomax_state(STATE_OFF)

    def turn_on_nowait(self) -> None:
        """Turn on the ecoMAX controller without waiting."""
        self.create_task(self.turn_on())

    def turn_off_nowait(self) -> None:
        """Turn off the ecoMAX controller without waiting."""
        self.create_task(self.turn_off())

    async def shutdown(self) -> None:
        """Shutdown tasks for the ecoMAX controller and sub-devices."""
        mixers: dict[str, Mixer] = self.get_nowait(ATTR_MIXERS, {})
        thermostats: dict[str, Thermostat] = self.get_nowait(ATTR_THERMOSTATS, {})
        devices = (mixers | thermostats).values()
        await asyncio.gather(*(device.shutdown() for device in devices))
        await super().shutdown()

    @event_listener(priority=0)
    async def on_event_setup(self, setup: bool) -> bool:
        """Request frames required to set up an ecoMAX entry."""
        _LOGGER.debug("Setting up device entry")

        try:
            await self.wait_for(ATTR_SENSORS, timeout=WAIT_FOR_SETUP_SECONDS)
        except asyncio.TimeoutError:
            _LOGGER.error(
                "Could not setup device entry; no response from device for %u seconds",
                WAIT_FOR_SETUP_SECONDS,
            )
            return False

        results = await asyncio.gather(
            *(self.request(key, frame_type) for key, frame_type in REQUIRED_KEYS),
            return_exceptions=True,
        )

        errors = [
            result.frame_type for result in results if isinstance(result, RequestError)
        ]

        if errors:
            self.dispatch_nowait(ATTR_FRAME_ERRORS, errors)

        _LOGGER.debug("Device entry setup done")
        return True

    @event_listener(priority=0)
    async def on_event_ecomax_parameters(
        self, parameters: list[tuple[int, ParameterValues]]
    ) -> bool:
        """Update ecoMAX parameters and dispatch the events."""
        _LOGGER.debug("Received device parameters")
        product_info: ProductInfo = await self.get(ATTR_PRODUCT)
        parameter_types = await get_ecomax_parameter_types(product_info)

        def _ecomax_parameter_events() -> Generator[Coroutine]:
            """Get dispatch calls for ecoMAX parameter events."""
            for index, values in parameters:
                try:
                    description = parameter_types[index]
                except IndexError:
                    _LOGGER.warning(
                        "Encountered unknown ecoMAX parameter (%i): %s. "
                        "Your device isn't fully compatible with this software "
                        "and may not work properly. Please visit the issue tracker "
                        "and open a feature request to support %s",
                        index,
                        values,
                        product_info.model,
                    )
                    return

                handler = (
                    EcomaxSwitch
                    if isinstance(description, EcomaxSwitchDescription)
                    else EcomaxNumber
                )
                yield self.dispatch(
                    description.name,
                    handler.create_or_update(
                        device=self, description=description, values=values, index=index
                    ),
                )

        await asyncio.gather(*_ecomax_parameter_events())
        return True

    @event_listener(priority=0)
    async def on_event_fuel_consumption(self, fuel_consumption: float) -> None:
        """Update the amount of burned fuel."""
        fuel_burned = self._fuel_meter.calculate(fuel_consumption)
        if fuel_burned is not None:
            self.dispatch_nowait(ATTR_FUEL_BURNED, fuel_burned)

    @event_listener(priority=0)
    async def on_event_mixer_parameters(
        self, parameters: dict[int, Any] | None
    ) -> bool:
        """Handle mixer parameters and dispatch the events."""
        _LOGGER.debug("Received mixer parameters")
        if parameters:
            await asyncio.gather(
                *(
                    mixer.dispatch(ATTR_MIXER_PARAMETERS, parameters[mixer.index])
                    for mixer in self._mixers(indexes=parameters.keys())
                )
            )
            return True

        return False

    @event_listener(priority=0)
    async def on_event_mixer_sensors(self, sensors: dict[int, Any] | None) -> bool:
        """Update mixer sensors and dispatch the events."""
        _LOGGER.debug("Received mixer sensors")
        if sensors:
            await asyncio.gather(
                *(
                    mixer.dispatch(ATTR_MIXER_SENSORS, sensors[mixer.index])
                    for mixer in self._mixers(indexes=sensors.keys())
                )
            )
            return True

        return False

    @event_listener(priority=0)
    async def on_event_schedule_parameters(
        self, parameters: list[tuple[int, ParameterValues]]
    ) -> bool:
        """Update schedule parameters and dispatch the events."""

        def _schedule_parameter_events() -> Generator[Coroutine]:
            """Get dispatch calls for schedule parameter events."""
            for index, values in parameters:
                description = SCHEDULE_PARAMETERS[index]
                handler = (
                    ScheduleSwitch
                    if isinstance(description, ScheduleSwitchDescription)
                    else ScheduleNumber
                )
                yield self.dispatch(
                    description.name,
                    handler.create_or_update(
                        device=self, description=description, values=values, index=index
                    ),
                )

        await asyncio.gather(*_schedule_parameter_events())
        return True

    @event_listener(priority=0)
    async def on_event_sensors(self, sensors: dict[str, Any]) -> bool:
        """Update ecoMAX sensors and dispatch the events."""
        _LOGGER.debug("Received device sensors")
        await asyncio.gather(
            *(self.dispatch(name, value) for name, value in sensors.items())
        )
        return True

    @event_listener(priority=0)
    async def on_event_thermostat_parameters(
        self, parameters: dict[int, Any] | None
    ) -> bool:
        """Handle thermostat parameters and dispatch the events."""
        _LOGGER.debug("Received thermostat parameters")
        if parameters:
            await asyncio.gather(
                *(
                    thermostat.dispatch(
                        ATTR_THERMOSTAT_PARAMETERS, parameters[thermostat.index]
                    )
                    for thermostat in self._thermostats(indexes=parameters.keys())
                )
            )
            return True

        return False

    @event_listener(priority=0)
    async def on_event_thermostat_profile(
        self, values: ParameterValues | None
    ) -> EcomaxNumber | None:
        """Update thermostat profile parameter."""
        if values:
            return EcomaxNumber(
                device=self, description=THERMOSTAT_PROFILE_PARAMETER, values=values
            )

        return None

    @event_listener(priority=0)
    async def on_event_thermostat_sensors(self, sensors: dict[int, Any] | None) -> bool:
        """Update thermostat sensors and dispatch the events."""
        _LOGGER.debug("Received thermostat sensors")
        if sensors:
            await asyncio.gather(
                *(
                    thermostat.dispatch(
                        ATTR_THERMOSTAT_SENSORS, sensors[thermostat.index]
                    )
                    for thermostat in self._thermostats(indexes=sensors.keys())
                ),
                return_exceptions=True,
            )
            return True

        return False

    @event_listener(priority=0)
    async def on_event_schedules(
        self, schedules: list[tuple[int, list[list[bool]]]]
    ) -> dict[str, Schedule]:
        """Update schedules."""
        _LOGGER.debug("Received device schedules")
        return {
            SCHEDULES[index]: Schedule(
                name=SCHEDULES[index],
                device=self,
                monday=ScheduleDay.from_iterable(schedule[1]),
                tuesday=ScheduleDay.from_iterable(schedule[2]),
                wednesday=ScheduleDay.from_iterable(schedule[3]),
                thursday=ScheduleDay.from_iterable(schedule[4]),
                friday=ScheduleDay.from_iterable(schedule[5]),
                saturday=ScheduleDay.from_iterable(schedule[6]),
                sunday=ScheduleDay.from_iterable(schedule[0]),
            )
            for index, schedule in schedules
        }

    @event_listener(filter=on_change, priority=0)
    async def on_event_state(self, state: DeviceState) -> None:
        """Update the ecoMAX control parameter."""
        await self.dispatch(
            ECOMAX_CONTROL_PARAMETER.name,
            EcomaxSwitch.create_or_update(
                description=ECOMAX_CONTROL_PARAMETER,
                device=self,
                values=ParameterValues(
                    value=int(state != DeviceState.OFF), min_value=0, max_value=1
                ),
            ),
        )


__all__ = ["ATTR_MIXERS", "ATTR_THERMOSTATS", "ATTR_FUEL_BURNED", "EcoMAX"]
