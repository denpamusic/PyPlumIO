"""Contains a mixer class."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine, Generator, Sequence
import logging
from typing import Any

from pyplumio.devices import VirtualDevice
from pyplumio.helpers.event_manager import EventListener, subscribe
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

_LOGGER = logging.getLogger(__name__)


class Mixer(VirtualDevice, EventListener):
    """Represents a mixer."""

    __slots__ = ()

    @subscribe(ATTR_MIXER_SENSORS)
    async def _update_mixer_sensors(self, sensors: dict[str, Any]) -> bool:
        """Update mixer sensors and dispatch the events."""
        await asyncio.gather(
            *(self.dispatch(name, value) for name, value in sensors.items())
        )
        return True

    @subscribe(ATTR_MIXER_PARAMETERS)
    async def _update_mixer_parameters(
        self, parameters: Sequence[tuple[int, ParameterValues]]
    ) -> bool:
        """Update mixer parameters and dispatch the events."""
        product: ProductInfo = await self.parent.get(ATTR_PRODUCT)

        def _mixer_parameter_events() -> Generator[Coroutine, Any, None]:
            """Get dispatch calls for mixer parameter events."""
            for index, values in parameters:
                try:
                    description = MIXER_PARAMETERS[product.type][index]
                except IndexError:
                    _LOGGER.warning(
                        "Encountered unknown mixer parameter (%i): %s. "
                        "Your device isn't fully compatible with this software "
                        "and may not work properly. Please visit the issue tracker "
                        "and open a feature request to support %s",
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


__all__ = ["Mixer"]
