"""Contains a thermostat class."""
from __future__ import annotations

import asyncio
from typing import Sequence

from pyplumio.devices import Addressable, SubDevice
from pyplumio.helpers.parameter import ParameterValues
from pyplumio.helpers.typing import EventDataType
from pyplumio.structures.thermostat_parameters import (
    ATTR_THERMOSTAT_PARAMETERS,
    THERMOSTAT_PARAMETERS,
    ThermostatBinaryParameter,
    ThermostatParameter,
)
from pyplumio.structures.thermostat_sensors import ATTR_THERMOSTAT_SENSORS


class Thermostat(SubDevice):
    """Represents a thermostat."""

    def __init__(self, queue: asyncio.Queue, parent: Addressable, index: int = 0):
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
            cls = (
                ThermostatBinaryParameter
                if description.is_binary
                else ThermostatParameter
            )
            await self.dispatch(
                description.name,
                cls(
                    device=self,
                    description=description,
                    index=index,
                    value=values.value,
                    min_value=values.min_value,
                    max_value=values.max_value,
                    offset=(self.index * len(parameters)),
                ),
            )

        return True
