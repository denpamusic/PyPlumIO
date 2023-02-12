"""Contains device representations."""
from __future__ import annotations

import asyncio
import logging
from typing import ClassVar
from warnings import warn

from pyplumio import util
from pyplumio.const import ATTR_LOADED, DeviceType, FrameType
from pyplumio.exceptions import ParameterNotFoundError, UnknownDeviceError
from pyplumio.frames import DataFrameDescription, Frame, Request, get_frame_handler
from pyplumio.helpers.event_manager import EventManager
from pyplumio.helpers.factory import factory
from pyplumio.helpers.parameter import SET_RETRIES, Parameter
from pyplumio.helpers.typing import ParameterValueType
from pyplumio.structures.network_info import ATTR_NETWORK, NetworkInfo

_LOGGER = logging.getLogger(__name__)


def _handler_class_path(device_type_name: str) -> str:
    """Return the handler class path for a given device type name."""
    device_type_name = util.to_camelcase(
        device_type_name, overrides={"ecomax": "EcoMAX", "ecoster": "EcoSTER"}
    )
    return f"{device_type_name.lower()}.{device_type_name}"


# dictionary of device handler classes indexed by device types.
# example: "69: ecomax.EcoMAX"
DEVICE_TYPES: dict[int, str] = {
    device_type.value: _handler_class_path(device_type.name)
    for device_type in DeviceType
}


def get_device_handler(device_type: int) -> str:
    """Return module and class for a given device type."""
    if device_type in DEVICE_TYPES:
        return "devices." + DEVICE_TYPES[device_type]

    raise UnknownDeviceError(f"Unknown device ({device_type})")


class Device(EventManager):
    """Represents a device."""

    queue: asyncio.Queue

    def __init__(self, queue: asyncio.Queue):
        """Initialize the device object."""
        super().__init__()
        self.queue = queue

    async def get_value(self, name: str, timeout: float | None = None):
        """Return a value."""
        warn(
            "get_value() is deprecated and will be removed in v0.4.1. "
            + "Please use get() or get_nowait().",
            DeprecationWarning,
            stacklevel=2,
        )

        value = await self.get(name, timeout)
        if isinstance(value, Parameter):
            return value.value

        return value

    async def get_parameter(self, name: str, timeout: float | None = None):
        """Return a parameter."""
        warn(
            "get_parameter() is deprecated and will be removed in v0.4.1. "
            + "Please use get() or get_nowait().",
            DeprecationWarning,
            stacklevel=2,
        )

        return await self.get(name, timeout)

    async def set_value(
        self, name: str, value: ParameterValueType, timeout: float | None = None
    ) -> bool:
        """Sets a value."""
        warn(
            "set_value() is deprecated and will be removed in v0.4.1. "
            + "Please use set().",
            DeprecationWarning,
            stacklevel=2,
        )

        return await self.set(name, value, timeout)

    def set_value_nowait(
        self, name: str, value: ParameterValueType, timeout: float | None = None
    ) -> None:
        """Sets a value without waiting."""
        warn(
            "set_value_nowait() is deprecated and will be removed in v0.4.1. "
            + "Please use set_nowait().",
            DeprecationWarning,
            stacklevel=2,
        )

        self.set_nowait(name, value, timeout)

    async def set(
        self,
        name: str,
        value: ParameterValueType,
        timeout: float | None = None,
        retries: int = SET_RETRIES,
    ) -> bool:
        """Set a parameter value. Name should point
        to a valid parameter object, otherwise raises
        ParameterNotFoundError."""
        parameter = await self.get(name, timeout=timeout)
        if not isinstance(parameter, Parameter):
            raise ParameterNotFoundError(f"Parameter not found ({name})")

        return await parameter.set(value, retries=retries)

    def set_nowait(
        self,
        name: str,
        value: ParameterValueType,
        timeout: float | None = None,
        retries: int = SET_RETRIES,
    ) -> None:
        """Set a parameter value without waiting for the result."""
        self.create_task(self.set(name, value, timeout, retries))


class Addressable(Device):
    """Represents the addressable device."""

    address: ClassVar[int]
    _network: NetworkInfo
    _frame_types: tuple[DataFrameDescription, ...] = ()

    def __init__(self, queue: asyncio.Queue, network: NetworkInfo):
        """Initialize the addressable object."""
        super().__init__(queue)
        self._network = network

    def handle_frame(self, frame: Frame) -> None:
        """Handle received frame."""
        if isinstance(frame, Request) and frame.frame_type in (
            FrameType.REQUEST_CHECK_DEVICE,
            FrameType.REQUEST_PROGRAM_VERSION,
        ):
            self.queue.put_nowait(frame.response(data={ATTR_NETWORK: self._network}))

        if frame.data is not None:
            for name, value in frame.data.items():
                self.dispatch_nowait(name, value)

    async def async_setup(self) -> bool:
        """Setup addressable device object."""
        try:
            await asyncio.gather(
                *{
                    self.create_task(
                        self.request(description.provides, description.frame_type)
                    )
                    for description in self._frame_types
                },
                return_exceptions=False,
            )
            await self.dispatch(ATTR_LOADED, True)
            return True
        except ValueError as e:
            _LOGGER.error("Request failed: %s", e)
            await self.dispatch(ATTR_LOADED, False)
            return False

    async def request(
        self,
        name: str,
        frame_type: FrameType,
        retries: int = 3,
        timeout: float = 3.0,
    ):
        """Send request for a data and wait for a value to become
        available. If value is not available before timeout, retry
        request."""
        request: Request = factory(
            get_frame_handler(frame_type), recipient=self.address
        )
        while retries > 0:
            try:
                self.queue.put_nowait(request)
                return await self.get(name, timeout=timeout)
            except asyncio.TimeoutError:
                retries -= 1

        raise ValueError(f'could not request "{name}" with "{frame_type.name}"')


class SubDevice(Device):
    """Represents the sub-device."""

    parent: Addressable
    index: int

    def __init__(self, queue: asyncio.Queue, parent: Addressable, index: int = 0):
        """Initialize a new sub-device object."""
        super().__init__(queue)
        self.parent = parent
        self.index = index


class Mixer(SubDevice):
    """Represents the mixer sub-device."""


class Thermostat(SubDevice):
    """Represents the thermostat sub-device."""
