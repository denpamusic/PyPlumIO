"""Contains a mixer class."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine, Generator
import logging
from typing import Any

from pyplumio.devices import LogicalDevice
from pyplumio.helpers.event_manager import event_listener
from pyplumio.parameters import ParameterValues
from pyplumio.parameters.mixer import (
    MixerNumber,
    MixerSwitch,
    MixerSwitchDescription,
    get_mixer_parameter_types,
)
from pyplumio.structures.product_info import ATTR_PRODUCT, ProductInfo

_LOGGER = logging.getLogger(__name__)


class Mixer(LogicalDevice):
    """Represents a mixer."""

    __slots__ = ()

    @event_listener
    async def on_event_mixer_sensors(self, sensors: dict[str, Any]) -> bool:
        """Update mixer sensors and dispatch the events."""
        _LOGGER.debug("Received mixer %i sensors", self.index)
        await asyncio.gather(
            *(self.dispatch(name, value) for name, value in sensors.items())
        )
        return True

    @event_listener
    async def on_event_mixer_parameters(
        self, parameters: list[tuple[int, ParameterValues]]
    ) -> bool:
        """Update mixer parameters and dispatch the events."""
        _LOGGER.debug("Received mixer %i parameters", self.index)
        product_info: ProductInfo = await self.parent.get(ATTR_PRODUCT)
        parameter_types = get_mixer_parameter_types(product_info)

        def _mixer_parameter_events() -> Generator[Coroutine]:
            """Get dispatch calls for mixer parameter events."""
            for index, values in parameters:
                try:
                    description = parameter_types[index]
                except IndexError:
                    _LOGGER.warning(
                        "Encountered unknown mixer parameter (%i): %s. "
                        "Your device isn't fully compatible with this software "
                        "and may not work properly. Please visit the issue tracker "
                        "and open a feature request to support %s",
                        index,
                        values,
                        product_info.model,
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


__all__ = ["Mixer"]
