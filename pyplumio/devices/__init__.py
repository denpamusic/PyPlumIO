"""Contains device representations."""
from __future__ import annotations

import asyncio
import logging
from typing import ClassVar

from pyplumio import util
from pyplumio.const import ATTR_LOADED, DeviceType, FrameType
from pyplumio.exceptions import ParameterNotFoundError, UnknownDeviceError
from pyplumio.frames import DataFrameDescription, Frame, Request, get_frame_handler
from pyplumio.helpers.factory import factory
from pyplumio.helpers.network_info import NetworkInfo
from pyplumio.helpers.parameter import Parameter
from pyplumio.helpers.task_manager import TaskManager
from pyplumio.helpers.typing import DeviceDataType, NumericType, SensorCallbackType
from pyplumio.structures.network_info import ATTR_NETWORK

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


class Device(TaskManager):
    """Represents a device."""

    queue: asyncio.Queue
    data: DeviceDataType
    _callbacks: dict[str, list[SensorCallbackType]]

    def __init__(self, queue: asyncio.Queue):
        """Initialize the device object."""
        super().__init__()
        self.data = {}
        self.queue = queue
        self._callbacks = {}

    async def get_value(self, name: str, timeout: float | None = None):
        """Return a value. When used with parameter, only it's
        value will be returned. To get the parameter object,
        get_parameter() method must be used instead."""
        if name not in self.data:
            await asyncio.wait_for(self.create_event(name).wait(), timeout=timeout)

        value = self.data[name]
        return value.value if isinstance(value, Parameter) else value

    async def get_parameter(self, name: str, timeout: float | None = None) -> Parameter:
        """Return a parameter."""
        if name not in self.data:
            await asyncio.wait_for(self.create_event(name).wait(), timeout=timeout)

        parameter = self.data[name]
        if isinstance(parameter, Parameter):
            return parameter

        raise ParameterNotFoundError(f"Parameter not found ({name})")

    async def set_value(
        self, name: str, value: NumericType, timeout: float | None = None
    ) -> bool:
        """set a parameter value. Name should point
        to a valid parameter object, otherwise raises
        ParameterNotFoundError."""
        if name not in self.data:
            await asyncio.wait_for(self.create_event(name).wait(), timeout=timeout)

        parameter = self.data[name]
        if not isinstance(parameter, Parameter):
            raise ParameterNotFoundError(f"Parameter not found ({name})")

        return await parameter.set(value)

    def set_value_nowait(
        self, name: str, value: NumericType, timeout: float | None = None
    ) -> None:
        """set a parameter value without waiting for the result."""
        self.create_task(self.set_value(name, value, timeout))

    def subscribe(self, name: str, callback: SensorCallbackType) -> None:
        """Subscribe a callback to the value change event."""
        if name not in self._callbacks:
            self._callbacks[name] = []

        self._callbacks[name].append(callback)

    def subscribe_once(self, name: str, callback: SensorCallbackType) -> None:
        """Subscribe a callback to the single value change event."""

        async def _callback(value):
            """Unsubscribe the callback and call it."""
            self.unsubscribe(name, _callback)
            return await callback(value)

        self.subscribe(name, _callback)

    def unsubscribe(self, name: str, callback: SensorCallbackType) -> None:
        """Usubscribe a callback from the value change event."""
        if name in self._callbacks and callback in self._callbacks[name]:
            self._callbacks[name].remove(callback)

    async def async_set_device_data(self, name: str, value) -> None:
        """Asynchronously call registered callbacks on value change."""
        if name in self._callbacks:
            callbacks = self._callbacks[name].copy()
            for callback in callbacks:
                return_value = await callback(value)
                value = return_value if return_value is not None else value

        self.data[name] = value
        self.set_event(name)

    def set_device_data(self, *args, **kwargs) -> None:
        """Call registered callbacks on value change."""
        self.create_task(self.async_set_device_data(*args, **kwargs))

    async def shutdown(self) -> None:
        """Cancel scheduled tasks."""
        self.cancel_tasks()
        await self.wait_until_done()


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
                self.set_device_data(name, value)

    async def async_setup(self) -> bool:
        """Request initial data frames."""
        try:
            await asyncio.gather(
                *{
                    self.create_task(
                        self.make_request(description.provides, description.frame_type)
                    )
                    for description in self._frame_types
                },
                return_exceptions=False,
            )
            await self.async_set_device_data(ATTR_LOADED, True)
            return True
        except ValueError as e:
            _LOGGER.error("Request failed: %s", e)
            await self.async_set_device_data(ATTR_LOADED, False)
            return False

    async def make_request(
        self,
        name: str,
        frame_type: FrameType,
        retries: int = 3,
        timeout: float = 10,
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
                return await self.get_value(name, timeout=timeout)
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
