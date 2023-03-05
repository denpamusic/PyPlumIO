"""Contains thermostat device representation."""
from __future__ import annotations

import asyncio
from typing import Sequence

from pyplumio.devices import Addressable, SubDevice
from pyplumio.helpers.typing import EventDataType, ParameterDataType
from pyplumio.structures.thermostat_parameters import (
    ATTR_THERMOSTAT_PARAMETERS,
    THERMOSTAT_PARAMETERS,
)
from pyplumio.structures.thermostat_sensors import ATTR_THERMOSTAT_SENSORS


class Thermostat(SubDevice):
    """Represents the thermostat sub-device."""

    def __init__(self, queue: asyncio.Queue, parent: Addressable, index: int = 0):
        """Initialize a new Thermostat object."""
        super().__init__(queue, parent, index)
        self.subscribe(ATTR_THERMOSTAT_SENSORS, self._add_sensors)
        self.subscribe(ATTR_THERMOSTAT_PARAMETERS, self._add_parameters)

    async def _add_sensors(self, sensors: EventDataType) -> bool:
        """Add thermostat sensors."""
        for name, value in sensors.items():
            await self.dispatch(name, value)

        return True

    async def _add_parameters(
        self, parameters: Sequence[tuple[int, ParameterDataType]]
    ) -> bool:
        """Add thermostat parameters."""
        for index, value in parameters:
            description = THERMOSTAT_PARAMETERS[index]
            parameter = description.cls(
                device=self,
                description=description,
                index=index,
                value=value[0],
                min_value=value[1],
                max_value=value[2],
                offset=(self.index * len(parameters)),
            )
            await self.dispatch(description.name, parameter)

        return True
