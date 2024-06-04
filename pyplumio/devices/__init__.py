"""Contains device classes."""

from __future__ import annotations

from abc import ABC
import asyncio
from collections.abc import Iterable
from functools import cache
from typing import Any, ClassVar

from pyplumio.const import ATTR_FRAME_ERRORS, ATTR_LOADED, DeviceType, FrameType
from pyplumio.exceptions import UnknownDeviceError
from pyplumio.frames import DataFrameDescription, Frame, Request
from pyplumio.helpers.event_manager import EventManager
from pyplumio.helpers.factory import create_instance
from pyplumio.helpers.parameter import SET_RETRIES, Parameter
from pyplumio.helpers.typing import ParameterValueType
from pyplumio.structures.network_info import NetworkInfo
from pyplumio.utils import to_camelcase


@cache
def is_known_device_type(device_type: int) -> bool:
    """Check if device type is known."""
    try:
        DeviceType(device_type)
        return True
    except ValueError:
        return False


@cache
def get_device_handler(device_type: int) -> str:
    """Return module name and class name for a given device type."""
    if not is_known_device_type(device_type):
        raise UnknownDeviceError(f"Unknown device type ({device_type})")

    type_name = to_camelcase(
        DeviceType(device_type).name,
        overrides={"ecomax": "EcoMAX", "ecoster": "EcoSTER"},
    )
    return f"devices.{type_name.lower()}.{type_name}"


class Device(ABC, EventManager):
    """Represents a device."""

    queue: asyncio.Queue

    def __init__(self, queue: asyncio.Queue):
        """Initialize a new device."""
        super().__init__()
        self.queue = queue

    async def set(
        self,
        name: str,
        value: ParameterValueType,
        timeout: float | None = None,
        retries: int = SET_RETRIES,
    ) -> bool:
        """Set a parameter value.

        :param name: Name of the parameter
        :type name: str
        :param value: New value for the parameter
        :type value: int | float | bool | Literal["on"] | Literal["off"]
        :param timeout: Wait this amount of seconds for confirmation,
            defaults to `None`
        :type timeout: float, optional
        :param retries: Try setting parameter for this amount of
            times, defaults to 5
        :type retries: int, optional
        :return: `True` if parameter was successfully set, `False`
            otherwise.
        :rtype: bool
        :raise asyncio.TimeoutError: when waiting past specified timeout
        :raise ValueError: when a new value is outside of allowed range
        :raise TypeError: when found data is not valid parameter
        """
        parameter = await self.get(name, timeout=timeout)
        if not isinstance(parameter, Parameter):
            raise TypeError(f"{name} is not valid parameter")

        return await parameter.set(value, retries=retries)

    def set_nowait(
        self,
        name: str,
        value: ParameterValueType,
        timeout: float | None = None,
        retries: int = SET_RETRIES,
    ) -> None:
        """Set a parameter value without waiting for the result.

        :param name: Name of the parameter
        :type name: str
        :param value: New value for the parameter
        :type value: int | float | bool | Literal["on"] | Literal["off"]
        :param timeout: Wait this amount of seconds for confirmation.
            As this method operates in the background without waiting,
            this value is used to determine failure when
            retrying and doesn't block, defaults to `None`
        :type timeout: float, optional
        :param retries: Try setting parameter for this amount of
            times, defaults to 5
        :type retries: int, optional
        :return: `True` if parameter was successfully set, `False`
            otherwise.
        :rtype: bool
        """
        self.create_task(self.set(name, value, timeout, retries))

    async def shutdown(self) -> None:
        """Cancel device tasks."""
        self.cancel_tasks()
        await self.wait_until_done()


class AddressableDevice(Device, ABC):
    """Represents an addressable device."""

    address: ClassVar[int]
    _network: NetworkInfo
    _setup_frames: Iterable[DataFrameDescription]

    def __init__(self, queue: asyncio.Queue, network: NetworkInfo):
        """Initialize a new addressable device."""
        super().__init__(queue)
        self._network = network

    def __int__(self) -> int:
        """Return the device address."""
        return int(self.address)

    def handle_frame(self, frame: Frame) -> None:
        """Handle frame received from the device."""
        frame.sender_device = self
        if frame.data is not None:
            for name, value in frame.data.items():
                self.dispatch_nowait(name, value)

    async def async_setup(self) -> bool:
        """Set up addressable device."""
        results = await asyncio.gather(
            *{
                self.request(description.provides, description.frame_type)
                for description in self._setup_frames
            },
            return_exceptions=True,
        )

        errors = [
            result.args[1] for result in results if isinstance(result, ValueError)
        ]

        await self.dispatch(ATTR_FRAME_ERRORS, errors)
        await self.dispatch(ATTR_LOADED, True)
        return True

    async def request(
        self, name: str, frame_type: FrameType, retries: int = 3, timeout: float = 3.0
    ) -> Any:
        """Send request and wait for a value to become available.

        If value is not available before timeout, retry request.
        """
        request = await Request.create(frame_type, recipient=self.address)
        while retries > 0:
            try:
                self.queue.put_nowait(request)
                return await self.get(name, timeout=timeout)
            except asyncio.TimeoutError:
                retries -= 1

        raise ValueError(f'could not request "{name}"', frame_type)

    @classmethod
    async def create(cls, device_type: int, **kwargs: Any) -> AddressableDevice:
        """Create a device handler object."""
        return await create_instance(
            get_device_handler(device_type), cls=AddressableDevice, **kwargs
        )


class SubDevice(Device, ABC):
    """Represents a sub-device."""

    parent: AddressableDevice
    index: int

    def __init__(self, queue: asyncio.Queue, parent: AddressableDevice, index: int = 0):
        """Initialize a new sub-device."""
        super().__init__(queue)
        self.parent = parent
        self.index = index
