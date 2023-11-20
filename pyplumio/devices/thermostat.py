"""Contains a thermostat class."""
from __future__ import annotations

import asyncio
from typing import Sequence

from pyplumio.devices import AddressableDevice, SubDevice
from pyplumio.helpers.parameter import ParameterValues
from pyplumio.helpers.typing import EventDataType
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

    async def _handle_sensors(self, sensors: EventDataType) -> bool:
        """Handle thermostat sensors.

        For each sensor dispatch an event with the
        sensor's name and value.
        """
        for name, value in sensors.items():
            await self.dispatch(name, value)

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
            name = description.name
            if name in self.data:
                parameter: ThermostatParameter = self.data[name]
                parameter.values = values
                await self.dispatch(name, parameter)
                continue

            cls = (
                ThermostatBinaryParameter
                if isinstance(description, ThermostatBinaryParameterDescription)
                else ThermostatParameter
            )
            await self.dispatch(
                name,
                cls(
                    device=self,
                    values=values,
                    description=description,
                    index=index,
                    offset=(self.index * len(parameters)),
                ),
            )

        return True
