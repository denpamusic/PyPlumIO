"""Contains mixer device representation."""
from __future__ import annotations

import asyncio
from typing import Sequence

from pyplumio.const import ProductType
from pyplumio.devices import Addressable, SubDevice
from pyplumio.helpers.typing import EventDataType, ParameterDataType
from pyplumio.structures.mixer_parameters import (
    ATTR_MIXER_PARAMETERS,
    ECOMAX_I_MIXER_PARAMETERS,
    ECOMAX_P_MIXER_PARAMETERS,
)
from pyplumio.structures.mixer_sensors import ATTR_MIXER_SENSORS
from pyplumio.structures.product_info import ATTR_PRODUCT


class Mixer(SubDevice):
    """Represents the mixer sub-device."""

    def __init__(self, queue: asyncio.Queue, parent: Addressable, index: int = 0):
        """Initialize a new Mixer object."""
        super().__init__(queue, parent, index)
        self.subscribe(ATTR_MIXER_SENSORS, self._add_sensors)
        self.subscribe(ATTR_MIXER_PARAMETERS, self._add_parameters)

    async def _add_sensors(self, sensors: EventDataType) -> bool:
        """Add mixer sensors."""
        for name, value in sensors.items():
            await self.dispatch(name, value)

        return True

    async def _add_parameters(
        self, parameters: Sequence[tuple[int, ParameterDataType]]
    ) -> bool:
        """Add mixer parameters."""
        product = await self.parent.get(ATTR_PRODUCT)

        for index, value in parameters:
            description = (
                ECOMAX_P_MIXER_PARAMETERS[index]
                if product.type == ProductType.ECOMAX_P
                else ECOMAX_I_MIXER_PARAMETERS[index]
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
