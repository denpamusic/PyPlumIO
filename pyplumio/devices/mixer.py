"""Contains a mixer class."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine, Generator, Sequence
import logging
from typing import TYPE_CHECKING, Any

from pyplumio.devices import PhysicalDevice, VirtualDevice
from pyplumio.helpers.parameter import ParameterValues
from pyplumio.structures.mixer_parameters import (
    ATTR_MIXER_PARAMETERS,
    MIXER_PARAMETERS,
    MixerNumber,
    MixerSwitch,
    MixerSwitchDescription,
)
from pyplumio.structures.mixer_sensors import ATTR_MIXER_SENSORS
from pyplumio.structures.product_info import ATTR_PRODUCT, ProductInfo

if TYPE_CHECKING:
    from pyplumio.frames import Frame

_LOGGER = logging.getLogger(__name__)


class Mixer(VirtualDevice):
    """Represents a mixer."""

    def __init__(
        self, queue: asyncio.Queue[Frame], parent: PhysicalDevice, index: int = 0
    ) -> None:
        """Initialize a new mixer."""
        super().__init__(queue, parent, index)
        self.subscribe(ATTR_MIXER_SENSORS, self._handle_mixer_sensors)
        self.subscribe(ATTR_MIXER_PARAMETERS, self._handle_mixer_parameters)

    async def _handle_mixer_sensors(self, sensors: dict[str, Any]) -> bool:
        """Handle mixer sensors.

        For each sensor dispatch an event with the
        sensor's name and value.
        """
        await asyncio.gather(
            *(self.dispatch(name, value) for name, value in sensors.items())
        )
        return True

    async def _handle_mixer_parameters(
        self, parameters: Sequence[tuple[int, ParameterValues]]
    ) -> bool:
        """Handle mixer parameters.

        For each parameter dispatch an event with the
        parameter's name and value.
        """
        product: ProductInfo = await self.parent.get(ATTR_PRODUCT)

        def _mixer_parameter_events() -> Generator[Coroutine, Any, None]:
            """Get dispatch calls for mixer parameter events."""
            for index, values in parameters:
                try:
                    description = MIXER_PARAMETERS[product.type][index]
                except IndexError:
                    _LOGGER.warning(
                        (
                            "Encountered unknown mixer parameter (%i): %s. "
                            "Your device isn't fully compatible with this software and "
                            "may not work properly. "
                            "Please visit the issue tracker and open a feature "
                            "request to support %s"
                        ),
                        index,
                        values,
                        product.model,
                    )
                    return

                handler = (
                    MixerSwitch
                    if isinstance(description, MixerSwitchDescription)
                    else MixerNumber
                )
                yield self.dispatch(
                    description.name,
                    handler.create_or_update(
                        device=self, description=description, values=values, index=index
                    ),
                )

        await asyncio.gather(*_mixer_parameter_events())
        return True
