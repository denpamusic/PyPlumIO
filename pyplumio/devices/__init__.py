"""Contains device classes."""

from __future__ import annotations

from abc import ABC
import asyncio
from functools import cache
import logging
from typing import Any, ClassVar

from pyplumio.const import ATTR_FRAME_ERRORS, ATTR_LOADED, DeviceType, FrameType
from pyplumio.exceptions import RequestError, UnknownDeviceError
from pyplumio.filters import on_change
from pyplumio.frames import DataFrameDescription, Frame, Request, is_known_frame_type
from pyplumio.helpers.event_manager import EventManager, subscribe
from pyplumio.helpers.factory import create_instance
from pyplumio.helpers.parameter import NumericType, Parameter, State
from pyplumio.structures.frame_versions import ATTR_FRAME_VERSIONS
from pyplumio.structures.network_info import NetworkInfo
from pyplumio.utils import to_camelcase

_LOGGER = logging.getLogger(__name__)


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

    __slots__ = ("queue",)

    queue: asyncio.Queue[Frame]

    def __init__(self, queue: asyncio.Queue[Frame]) -> None:
        """Initialize a new device."""
        super().__init__()
        self.queue = queue

    async def set(
        self,
        name: str,
        value: NumericType | State | bool,
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
            raise TypeError(f"The parameter '{name}' is not valid or does not exist.")

        return await parameter.set(value, retries=retries)

    def set_nowait(
        self,
        name: str,
        value: NumericType | State | bool,
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

    __slots__ = ("address", "_network", "_setup_frames", "_frame_versions")

    address: ClassVar[int]
    _network: NetworkInfo
    _setup_frames: tuple[DataFrameDescription, ...]
    _frame_versions: dict[int, int]

    def __init__(self, queue: asyncio.Queue[Frame], network: NetworkInfo) -> None:
        """Initialize a new physical device."""
        super().__init__(queue)
        self._network = network
        self._frame_versions = {}

    @subscribe(ATTR_FRAME_VERSIONS, on_change)
    async def _update_frame_versions(self, versions: dict[int, int]) -> None:
        """Check frame versions and update outdated frames."""
        for frame_type, version in versions.items():
            if (
                is_known_frame_type(frame_type)
                and self.supports_frame_type(frame_type)
                and not self.has_frame_version(frame_type, version)
            ):
                _LOGGER.debug("Updating frame %s to version %i", frame_type, version)
                request = await Request.create(frame_type, recipient=self.address)
                self.queue.put_nowait(request)
                self._frame_versions[frame_type] = version

    def has_frame_version(self, frame_type: FrameType | int, version: int) -> bool:
        """Return True if frame data is up to date, False otherwise."""
        return (
            frame_type in self._frame_versions
            and self._frame_versions[frame_type] == version
        )

    def supports_frame_type(self, frame_type: int) -> bool:
        """Check if frame type is supported by the device."""
        return frame_type not in self.data.get(ATTR_FRAME_ERRORS, [])

    def handle_frame(self, frame: Frame) -> None:
        """Handle frame received from the device."""
        frame.assign_to(self)
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
            result.frame_type for result in results if isinstance(result, RequestError)
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

        raise RequestError(
            f"Failed to request '{name}' with frame type '{frame_type}' after "
            f"{retries} retries.",
            frame_type=frame_type,
        )

    @classmethod
    async def create(cls, device_type: int, **kwargs: Any) -> PhysicalDevice:
        """Create a physical device handler object."""
        return await create_instance(get_device_handler(device_type), cls=cls, **kwargs)


class VirtualDevice(Device, ABC):
    """Represents a virtual device associated with physical device."""

    __slots__ = ("parent", "index")

    parent: PhysicalDevice
    index: int

    def __init__(
        self, queue: asyncio.Queue[Frame], parent: PhysicalDevice, index: int = 0
    ) -> None:
        """Initialize a new sub-device."""
        super().__init__(queue)
        self.parent = parent
        self.index = index


__all__ = [
    "Device",
    "PhysicalDevice",
    "VirtualDevice",
    "is_known_device_type",
    "get_device_handler",
]
