"""Contains a thermostat class."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Any

from pyplumio.devices import AddressableDevice, SubDevice
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
        self.subscribe(ATTR_THERMOSTAT_SENSORS, self._handle_sensors)
        self.subscribe(ATTR_THERMOSTAT_PARAMETERS, self._handle_parameters)

    async def _handle_sensors(self, sensors: dict[str, Any]) -> bool:
        """Handle thermostat sensors.

        For each sensor dispatch an event with the
        sensor's name and value.
        """
        await asyncio.gather(
            *[self.dispatch(name, value) for name, value in sensors.items()]
        )

        return True

    async def _handle_parameters(
        self, parameters: Sequence[tuple[int, ParameterValues]]
    ) -> bool:
        """Handle thermostat parameters.

        For each parameter dispatch an event with the
        parameter's name and value.
        """
        for index, values in parameters:
            description = THERMOSTAT_PARAMETERS[index]
            if not (parameter := self.data.get(description.name, None)):
                handler = (
                    ThermostatBinaryParameter
                    if isinstance(description, ThermostatBinaryParameterDescription)
                    else ThermostatParameter
                )
                parameter = handler(
                    device=self,
                    description=description,
                    index=index,
                    offset=(self.index * len(parameters)),
                )

            parameter.update(values)
            await self.dispatch(description.name, parameter)

        return True
