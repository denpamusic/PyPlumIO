"""Contains a thermostat class."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine, Generator
import logging
from typing import Any

from pyplumio.devices import VirtualDevice
from pyplumio.helpers.event_manager import event_listener
from pyplumio.parameters import ParameterValues
from pyplumio.parameters.thermostat import (
    ThermostatNumber,
    ThermostatSwitch,
    ThermostatSwitchDescription,
    get_thermostat_parameter_types,
)

_LOGGER = logging.getLogger()


class Thermostat(VirtualDevice):
    """Represents a thermostat."""

    __slots__ = ()

    @event_listener
    async def on_event_thermostat_sensors(self, sensors: dict[str, Any]) -> bool:
        """Update thermostat sensors and dispatch the events."""
        _LOGGER.info("Received thermostat %i sensors", self.index)
        await asyncio.gather(
            *(self.dispatch(name, value) for name, value in sensors.items())
        )
        return True

    @event_listener
    async def on_event_thermostat_parameters(
        self, parameters: list[tuple[int, ParameterValues]]
    ) -> bool:
        """Update thermostat parameters and dispatch the events."""
        _LOGGER.info("Received thermostat %i parameters", self.index)

        def _thermostat_parameter_events() -> Generator[Coroutine, Any, None]:
            """Get dispatch calls for thermostat parameter events."""
            parameter_types = get_thermostat_parameter_types()
            for index, values in parameters:
                description = parameter_types[index]
                handler = (
                    ThermostatSwitch
                    if isinstance(description, ThermostatSwitchDescription)
                    else ThermostatNumber
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

        await asyncio.gather(*_thermostat_parameter_events())
        return True


__all__ = ["Thermostat"]
