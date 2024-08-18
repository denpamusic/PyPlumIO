"""Contains device classes."""

from __future__ import annotations

from abc import ABC
import asyncio
from functools import cache
from typing import Any, ClassVar

from pyplumio.const import ATTR_FRAME_ERRORS, ATTR_LOADED, DeviceType, FrameType
from pyplumio.exceptions import UnknownDeviceError
from pyplumio.frames import DataFrameDescription, Frame, Request
from pyplumio.helpers.event_manager import EventManager
from pyplumio.helpers.factory import create_instance
from pyplumio.helpers.parameter import Parameter, ParameterValue
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

    queue: asyncio.Queue[Frame]

    def __init__(self, queue: asyncio.Queue[Frame]):
        """Initialize a new device."""
        super().__init__()
        self.queue = queue

    async def set(
        self,
        name: str,
        value: ParameterValue,
        retries: int = 5,
        timeout: float | None = None,
    ) -> bool:
        """Set a parameter value.

        :param name: Name of the parameter
        :type name: str
        :param value: New value for the parameter
        :type value: int | float | bool | Literal["off", "on"]
        :param retries: Try setting parameter for this amount of
            times, defaults to 5
        :type retries: int, optional
        :param timeout: Wait this amount of seconds for confirmation,
            defaults to `None`
        :type timeout: float, optional
        :return: `True` if parameter was successfully set, `False`
            otherwise.
        :rtype: bool
        :raise asyncio.TimeoutError: when waiting past specified timeout
        :raise ValueError: when a new value is outside of allowed range
        :raise TypeError: when found data is not valid parameter
        """
        parameter = await self.get(name, timeout)
        if not isinstance(parameter, Parameter):
            raise TypeError(f"{name} is not valid parameter")

        return await parameter.set(value, retries=retries)

    def set_nowait(
        self,
        name: str,
        value: ParameterValue,
        retries: int = 5,
        timeout: float | None = None,
    ) -> None:
        """Set a parameter value without waiting for the result.

        :param name: Name of the parameter
        :type name: str
        :param value: New value for the parameter
        :type value: int | float | bool | Literal["off", "on"]
        :param retries: Try setting parameter for this amount of
            times, defaults to 5
        :type retries: int, optional
        :param timeout: Wait this amount of seconds for confirmation.
            As this method operates in the background without waiting,
            this value is used to determine failure when
            retrying and doesn't block, defaults to `None`
        :type timeout: float, optional
        :return: `True` if parameter was successfully set, `False`
            otherwise.
        :rtype: bool
        """
        self.create_task(self.set(name, value, retries, timeout))

    async def shutdown(self) -> None:
        """Cancel device tasks."""
        self.cancel_tasks()
        await self.wait_until_done()


class PhysicalDevice(Device, ABC):
    """Represents a physical device.

    Physical device have network address and can have multiple
    virtual devices associated with them via parent property.
    """

    address: ClassVar[int]
    _network: NetworkInfo
    _setup_frames: tuple[DataFrameDescription, ...]

    def __init__(self, queue: asyncio.Queue[Frame], network: NetworkInfo):
        """Initialize a new physical device."""
        super().__init__(queue)
        self._network = network

    def handle_frame(self, frame: Frame) -> None:
        """Handle frame received from the device."""
        frame.sender_device = self
        if frame.data is not None:
            for name, value in frame.data.items():
                self.dispatch_nowait(name, value)

    async def async_setup(self) -> bool:
        """Set up addressable device."""
        results = await asyncio.gather(
            *(
                self.request(description.provides, description.frame_type)
                for description in self._setup_frames
            ),
            return_exceptions=True,
        )

        errors = [
            result.args[1] for result in results if isinstance(result, BaseException)
        ]

        await asyncio.gather(
            self.dispatch(ATTR_FRAME_ERRORS, errors), self.dispatch(ATTR_LOADED, True)
        )
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
    async def create(cls, device_type: int, **kwargs: Any) -> PhysicalDevice:
        """Create a physical device handler object."""
        return await create_instance(get_device_handler(device_type), cls=cls, **kwargs)


class VirtualDevice(Device, ABC):
    """Represents a virtual device associated with physical device."""

    parent: PhysicalDevice
    index: int

    def __init__(
        self, queue: asyncio.Queue[Frame], parent: PhysicalDevice, index: int = 0
    ):
        """Initialize a new sub-device."""
        super().__init__(queue)
        self.parent = parent
        self.index = index
