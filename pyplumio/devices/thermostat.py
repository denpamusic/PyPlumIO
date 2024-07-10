"""Contains a thermostat class."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine, Generator, Sequence
from typing import Any

from pyplumio.devices import AddressableDevice, SubDevice
from pyplumio.helpers.event_manager import Event
from pyplumio.helpers.parameter import ParameterValues
from pyplumio.structures.thermostat_parameters import (
    ATTR_THERMOSTAT_PARAMETERS,
    THERMOSTAT_PARAMETERS,
    ThermostatBinaryParameter,
    ThermostatBinaryParameterDescription,
    ThermostatParameter,
)
from pyplumio.structures.thermostat_sensors import ATTR_THERMOSTAT_SENSORS


class Thermostat(SubDevice):
    """Represents a thermostat."""

    def __init__(self, queue: asyncio.Queue, parent: AddressableDevice, index: int = 0):
        """Initialize a new thermostat."""
        super().__init__(queue, parent, index)
        self.subscribe(ATTR_THERMOSTAT_SENSORS, self._handle_thermostat_sensors)
        self.subscribe(ATTR_THERMOSTAT_PARAMETERS, self._handle_thermostat_parameters)

    async def _handle_thermostat_sensors(self, event: Event) -> bool:
        """Handle thermostat sensors.

        For each sensor dispatch an event with the
        sensor's name and value.
        """

        def _thermostat_sensor_events(
            sensors: dict[str, Any],
        ) -> Generator[Coroutine, Any, None]:
            """Get dispatch calls for thermostat sensors events."""
            for name, value in sensors.items():
                yield self.dispatch(name, value)

        await asyncio.gather(*_thermostat_sensor_events(event.data))
        return True

    async def _handle_thermostat_parameters(self, event: Event) -> bool:
        """Handle thermostat parameters.

        For each parameter dispatch an event with the
        parameter's name and value.
        """

        def _thermostat_parameter_events(
            parameters: Sequence[tuple[int, ParameterValues]],
        ) -> Generator[Coroutine, Any, None]:
            """Get dispatch calls for thermostat parameter events."""
            for index, values in parameters:
                description = THERMOSTAT_PARAMETERS[index]
                handler = (
                    ThermostatBinaryParameter
                    if isinstance(description, ThermostatBinaryParameterDescription)
                    else ThermostatParameter
                )
                yield self.dispatch(
                    description.name,
                    handler.create_or_update(
                        device=self,
                        description=description,
                        values=values,
                        index=index,
                        offset=(self.index * len(parameters)),
                    ),
                )

        await asyncio.gather(*_thermostat_parameter_events(event.data))
        return True
