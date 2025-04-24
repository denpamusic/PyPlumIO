"""Contains a mixer class."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine, Generator, Sequence
import logging
from typing import Any

from pyplumio.devices import VirtualDevice
from pyplumio.helpers.event_manager import event_listener
from pyplumio.parameters import ParameterValues
from pyplumio.parameters.mixer import (
    MixerNumber,
    MixerSwitch,
    MixerSwitchDescription,
    get_mixer_parameter_types,
)
from pyplumio.structures.mixer_parameters import ATTR_MIXER_PARAMETERS
from pyplumio.structures.mixer_sensors import ATTR_MIXER_SENSORS
from pyplumio.structures.product_info import ATTR_PRODUCT, ProductInfo

_LOGGER = logging.getLogger(__name__)


class Mixer(VirtualDevice):
    """Represents a mixer."""

    __slots__ = ()

    @event_listener(ATTR_MIXER_SENSORS)
    async def on_event_mixer_sensors(self, sensors: dict[str, Any]) -> bool:
        """Update mixer sensors and dispatch the events."""
        await asyncio.gather(
            *(self.dispatch(name, value) for name, value in sensors.items())
        )
        return True

    @event_listener(ATTR_MIXER_PARAMETERS)
    async def on_event_mixer_parameters(
        self, parameters: Sequence[tuple[int, ParameterValues]]
    ) -> bool:
        """Update mixer parameters and dispatch the events."""
        product_info: ProductInfo = await self.parent.get(ATTR_PRODUCT)

        def _mixer_parameter_events() -> Generator[Coroutine, Any, None]:
            """Get dispatch calls for mixer parameter events."""
            parameter_types = get_mixer_parameter_types(product_info)
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
