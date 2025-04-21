"""Contains an ecoMAX class."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine, Generator, Iterable, Sequence
import logging
import time
from typing import Any, Final

from pyplumio.const import (
    ATTR_PASSWORD,
    ATTR_SENSORS,
    ATTR_STATE,
    DeviceState,
    DeviceType,
    FrameType,
)
from pyplumio.devices import PhysicalDevice
from pyplumio.devices.mixer import Mixer
from pyplumio.devices.thermostat import Thermostat
from pyplumio.filters import on_change
from pyplumio.frames import DataFrameDescription, Frame, Request
from pyplumio.helpers.event_manager import EventListener, subscribe
from pyplumio.helpers.parameter import STATE_OFF, STATE_ON, ParameterValues, State
from pyplumio.helpers.schedule import Schedule, ScheduleDay
from pyplumio.structures.alerts import ATTR_TOTAL_ALERTS
from pyplumio.structures.ecomax_parameters import (
    ATTR_ECOMAX_CONTROL,
    ATTR_ECOMAX_PARAMETERS,
    ECOMAX_CONTROL_PARAMETER,
    ECOMAX_PARAMETERS,
    THERMOSTAT_PROFILE_PARAMETER,
    EcomaxNumber,
    EcomaxSwitch,
    EcomaxSwitchDescription,
)
from pyplumio.structures.fuel_consumption import ATTR_FUEL_CONSUMPTION
from pyplumio.structures.mixer_parameters import ATTR_MIXER_PARAMETERS
from pyplumio.structures.mixer_sensors import ATTR_MIXER_SENSORS
from pyplumio.structures.network_info import ATTR_NETWORK, NetworkInfo
from pyplumio.structures.product_info import ATTR_PRODUCT, ProductInfo
from pyplumio.structures.regulator_data_schema import ATTR_REGDATA_SCHEMA
from pyplumio.structures.schedules import (
    ATTR_SCHEDULE_PARAMETERS,
    ATTR_SCHEDULES,
    SCHEDULE_PARAMETERS,
    SCHEDULES,
    ScheduleNumber,
    ScheduleSwitch,
    ScheduleSwitchDescription,
)
from pyplumio.structures.thermostat_parameters import (
    ATTR_THERMOSTAT_PARAMETERS,
    ATTR_THERMOSTAT_PROFILE,
)
from pyplumio.structures.thermostat_sensors import ATTR_THERMOSTAT_SENSORS

ATTR_MIXERS: Final = "mixers"
ATTR_THERMOSTATS: Final = "thermostats"
ATTR_FUEL_BURNED: Final = "fuel_burned"

NANOSECONDS_IN_SECOND: Final = 1_000_000_000
MAX_TIME_SINCE_LAST_FUEL_UPDATE_NS: Final = 300 * NANOSECONDS_IN_SECOND

SETUP_FRAME_TYPES: tuple[DataFrameDescription, ...] = (
    DataFrameDescription(
        frame_type=FrameType.REQUEST_UID,
        provides=ATTR_PRODUCT,
    ),
    DataFrameDescription(
        frame_type=FrameType.REQUEST_REGULATOR_DATA_SCHEMA,
        provides=ATTR_REGDATA_SCHEMA,
    ),
    DataFrameDescription(
        frame_type=FrameType.REQUEST_ECOMAX_PARAMETERS,
        provides=ATTR_ECOMAX_PARAMETERS,
    ),
    DataFrameDescription(
        frame_type=FrameType.REQUEST_ALERTS,
        provides=ATTR_TOTAL_ALERTS,
    ),
    DataFrameDescription(
        frame_type=FrameType.REQUEST_SCHEDULES,
        provides=ATTR_SCHEDULES,
    ),
    DataFrameDescription(
        frame_type=FrameType.REQUEST_MIXER_PARAMETERS,
        provides=ATTR_MIXER_PARAMETERS,
    ),
    DataFrameDescription(
        frame_type=FrameType.REQUEST_THERMOSTAT_PARAMETERS,
        provides=ATTR_THERMOSTAT_PARAMETERS,
    ),
    DataFrameDescription(
        frame_type=FrameType.REQUEST_PASSWORD,
        provides=ATTR_PASSWORD,
    ),
)

_LOGGER = logging.getLogger(__name__)


class EcoMAX(PhysicalDevice, EventListener):
    """Represents an ecoMAX controller."""

    __slots__ = ("_fuel_burned_time_ns",)

    address = DeviceType.ECOMAX
    _setup_frames = SETUP_FRAME_TYPES

    _fuel_burned_time_ns: int

    def __init__(self, queue: asyncio.Queue[Frame], network: NetworkInfo) -> None:
        """Initialize a new ecoMAX controller."""
        super().__init__(queue, network)
        self._fuel_burned_time_ns = time.perf_counter_ns()

    async def async_setup(self) -> bool:
        """Set up an ecoMAX controller."""
        await self.wait_for(ATTR_SENSORS)
        return await super().async_setup()

    def handle_frame(self, frame: Frame) -> None:
        """Handle frame received from the ecoMAX device."""
        if isinstance(frame, Request) and (
            response := frame.response(data={ATTR_NETWORK: self._network})
        ):
            self.queue.put_nowait(response)

        super().handle_frame(frame)

    def _mixers(self, indexes: Iterable[int]) -> Generator[Mixer, None, None]:
        """Iterate through the mixer indexes.

        For each index, return or create an instance of the mixer class.
        Once done, dispatch the 'mixers' event without waiting.
        """
        mixers: dict[int, Mixer] = self.data.setdefault(ATTR_MIXERS, {})
        for index in indexes:
            yield mixers.setdefault(index, Mixer(self.queue, parent=self, index=index))

        return self.dispatch_nowait(ATTR_MIXERS, mixers)

    def _thermostats(self, indexes: Iterable[int]) -> Generator[Thermostat, None, None]:
        """Iterate through the thermostat indexes.

        For each index, return or create an instance of the thermostat
        class. Once done, dispatch the 'thermostats' event without
        waiting.
        """
        thermostats: dict[int, Thermostat] = self.data.setdefault(ATTR_THERMOSTATS, {})
        for index in indexes:
            yield thermostats.setdefault(
                index, Thermostat(self.queue, parent=self, index=index)
            )

        return self.dispatch_nowait(ATTR_THERMOSTATS, thermostats)

    @subscribe(ATTR_ECOMAX_PARAMETERS)
    async def _update_ecomax_parameters(
        self, parameters: Sequence[tuple[int, ParameterValues]]
    ) -> bool:
        """Update ecoMAX parameters and dispatch the events."""
        product: ProductInfo = await self.get(ATTR_PRODUCT)

        def _ecomax_parameter_events() -> Generator[Coroutine, Any, None]:
            """Get dispatch calls for ecoMAX parameter events."""
            for index, values in parameters:
                try:
                    description = ECOMAX_PARAMETERS[product.type][index]
                except IndexError:
                    _LOGGER.warning(
                        "Encountered unknown ecoMAX parameter (%i): %s. "
                        "Your device isn't fully compatible with this software "
                        "and may not work properly. Please visit the issue tracker "
                        "and open a feature request to support %s",
                        index,
                        values,
                        product.model,
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

    @subscribe(ATTR_FUEL_CONSUMPTION)
    async def _update_burned_fuel_counter(self, fuel_consumption: float) -> None:
        """Update the amount fuel burned.

        This method calculates the fuel burned based on the time
        elapsed since the last sensor message, which contains fuel
        consumption data. If the elapsed time is within the acceptable
        range, it dispatches the fuel burned data. Otherwise, it logs a
        warning and skips the outdated data.
        """
        time_ns = time.perf_counter_ns()
        nanoseconds_passed = time_ns - self._fuel_burned_time_ns
        self._fuel_burned_time_ns = time_ns
        if nanoseconds_passed < MAX_TIME_SINCE_LAST_FUEL_UPDATE_NS:
            return self.dispatch_nowait(
                ATTR_FUEL_BURNED,
                fuel_consumption * nanoseconds_passed / (3600 * NANOSECONDS_IN_SECOND),
            )

        _LOGGER.warning(
            "Skipping outdated fuel consumption data: %f (was %i seconds old)",
            fuel_consumption,
            nanoseconds_passed / NANOSECONDS_IN_SECOND,
        )

    @subscribe(ATTR_MIXER_PARAMETERS)
    async def _update_mixer_parameters(
        self,
        parameters: dict[int, Sequence[tuple[int, ParameterValues]]] | None,
    ) -> bool:
        """Handle mixer parameters and dispatch the events."""
        if parameters:
            await asyncio.gather(
                *(
                    mixer.dispatch(ATTR_MIXER_PARAMETERS, parameters[mixer.index])
                    for mixer in self._mixers(indexes=parameters.keys())
                )
            )
            return True

        return False

    @subscribe(ATTR_MIXER_SENSORS)
    async def _update_mixer_sensors(
        self, sensors: dict[int, dict[str, Any]] | None
    ) -> bool:
        """Update mixer sensors and dispatch the events."""
        if sensors:
            await asyncio.gather(
                *(
                    mixer.dispatch(ATTR_MIXER_SENSORS, sensors[mixer.index])
                    for mixer in self._mixers(indexes=sensors.keys())
                )
            )
            return True

        return False

    @subscribe(ATTR_SCHEDULES, on_change)
    async def _update_schedules(
        self, schedules: list[tuple[int, list[list[bool]]]]
    ) -> dict[str, Schedule]:
        """Update schedules."""
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

    @subscribe(ATTR_SCHEDULE_PARAMETERS)
    async def _update_schedule_parameters(
        self, parameters: Sequence[tuple[int, ParameterValues]]
    ) -> bool:
        """Update schedule parameters and dispatch the events."""

        def _schedule_parameter_events() -> Generator[Coroutine, Any, None]:
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

    @subscribe(ATTR_SENSORS)
    async def _update_ecomax_sensors(self, sensors: dict[str, Any]) -> bool:
        """Update ecoMAX sensors and dispatch the events."""
        await asyncio.gather(
            *(self.dispatch(name, value) for name, value in sensors.items())
        )
        return True

    @subscribe(ATTR_STATE, on_change)
    async def _update_ecomax_control_parameter(self, mode: DeviceState) -> None:
        """Update the ecoMAX control parameter."""
        await self.dispatch(
            ECOMAX_CONTROL_PARAMETER.name,
            EcomaxSwitch.create_or_update(
                description=ECOMAX_CONTROL_PARAMETER,
                device=self,
                values=ParameterValues(
                    value=int(mode != DeviceState.OFF), min_value=0, max_value=1
                ),
            ),
        )

    @subscribe(ATTR_THERMOSTAT_PARAMETERS)
    async def _update_thermostat_parameters(
        self,
        parameters: dict[int, Sequence[tuple[int, ParameterValues]]] | None,
    ) -> bool:
        """Handle thermostat parameters and dispatch the events."""
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

    @subscribe(ATTR_THERMOSTAT_PROFILE)
    async def _update_thermostat_profile_parameter(
        self, values: ParameterValues | None
    ) -> EcomaxNumber | None:
        """Update thermostat profile parameter."""
        if values:
            return EcomaxNumber(
                device=self, description=THERMOSTAT_PROFILE_PARAMETER, values=values
            )

        return None

    @subscribe(ATTR_THERMOSTAT_SENSORS)
    async def _update_thermostat_sensors(
        self, sensors: dict[int, dict[str, Any]] | None
    ) -> bool:
        """Update thermostat sensors and dispatch the events."""
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

    async def _set_ecomax_state(self, state: State) -> bool:
        """Try to set the ecoMAX control state."""
        try:
            switch: EcomaxSwitch = self.data[ATTR_ECOMAX_CONTROL]
            return await switch.set(state)
        except KeyError:
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


__all__ = ["ATTR_MIXERS", "ATTR_THERMOSTATS", "ATTR_FUEL_BURNED", "EcoMAX"]
