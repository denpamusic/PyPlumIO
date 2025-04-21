"""Contains a thermostat class."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine, Generator, Sequence
from typing import Any

from pyplumio.devices import VirtualDevice
from pyplumio.helpers.event_manager import EventListener, subscribe
from pyplumio.helpers.parameter import ParameterValues
from pyplumio.structures.thermostat_parameters import (
    ATTR_THERMOSTAT_PARAMETERS,
    THERMOSTAT_PARAMETERS,
    ThermostatNumber,
    ThermostatSwitch,
    ThermostatSwitchDescription,
)
from pyplumio.structures.thermostat_sensors import ATTR_THERMOSTAT_SENSORS


class Thermostat(VirtualDevice, EventListener):
    """Represents a thermostat."""

    __slots__ = ()

    @subscribe(ATTR_THERMOSTAT_SENSORS)
    async def _update_thermostat_sensors(self, sensors: dict[str, Any]) -> bool:
        """Handle thermostat sensors.

        For each sensor dispatch an event with the
        sensor's name and value.
        """
        await asyncio.gather(
            *(self.dispatch(name, value) for name, value in sensors.items())
        )
        return True

    @subscribe(ATTR_THERMOSTAT_PARAMETERS)
    async def _update_thermostat_parameters(
        self, parameters: Sequence[tuple[int, ParameterValues]]
    ) -> bool:
        """Handle thermostat parameters.

        For each parameter dispatch an event with the
        parameter's name and value.
        """

        def _thermostat_parameter_events() -> Generator[Coroutine, Any, None]:
            """Get dispatch calls for thermostat parameter events."""
            for index, values in parameters:
                description = THERMOSTAT_PARAMETERS[index]
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
