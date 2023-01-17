"""Contains device representations."""
from __future__ import annotations

import asyncio
from typing import ClassVar, Dict, List, Optional

from pyplumio import util
from pyplumio.const import DeviceType
from pyplumio.exceptions import ParameterNotFoundError, UnknownDeviceError
from pyplumio.frames import Frame, Request
from pyplumio.helpers.parameter import Parameter
from pyplumio.helpers.task_manager import TaskManager
from pyplumio.helpers.typing import DeviceDataType, NumericType, SensorCallbackType


def _handler_class_path(device_type_name: str) -> str:
    """Return the handler class path for a given device type name."""
    device_type_name = util.to_camelcase(
        device_type_name, overrides={"ecomax": "EcoMAX", "ecoster": "EcoSTER"}
    )
    return f"{device_type_name.lower()}.{device_type_name}"


# Dictionary of device handler classes indexed by device types.
# example: "69: ecomax.EcoMAX"
DEVICE_TYPES: Dict[int, str] = {
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
    _callbacks: Dict[str, List[SensorCallbackType]]

    def __init__(self, queue: asyncio.Queue):
        """Initialize the device object."""
        super().__init__()
        self.data = {}
        self.queue = queue
        self._callbacks = {}

    async def get_value(self, name: str, timeout: Optional[float] = None):
        """Return a value. When used with parameter, only it's
        value will be returned. To get the parameter object,
        get_parameter() method must be used instead."""
        if name not in self.data:
            await asyncio.wait_for(self.create_event(name).wait(), timeout=timeout)

        value = self.data[name]
        return value.value if isinstance(value, Parameter) else value

    async def get_parameter(
        self, name: str, timeout: Optional[float] = None
    ) -> Parameter:
        """Return a parameter."""
        if name not in self.data:
            await asyncio.wait_for(self.create_event(name).wait(), timeout=timeout)

        parameter = self.data[name]
        if isinstance(parameter, Parameter):
            return parameter

        raise ParameterNotFoundError(f"Parameter not found ({name})")

    async def set_value(
        self,
        name: str,
        value: NumericType,
        timeout: Optional[float] = None,
        await_confirmation: bool = True,
    ) -> bool:
        """Set a parameter value. Name should point
        to a valid parameter object, otherwise raises
        ParameterNotFoundError."""
        if name not in self.data:
            await asyncio.wait_for(self.create_event(name).wait(), timeout=timeout)

        parameter = self.data[name]
        if not isinstance(parameter, Parameter):
            raise ParameterNotFoundError(f"Parameter not found ({name})")

        if await_confirmation:
            return await parameter.set(value)

        self.create_task(parameter.set(value))
        return True

    async def wait_for_data(
        self,
        name: str,
        request: Request,
        retries: int = 3,
        timeout: float = 5.0,
    ):
        """Waits until value present in device data.
        If value is not available before timeout, puts request for it
        in the device queue."""
        while retries > 0:
            try:
                return await self.get_value(name, timeout=timeout)
            except asyncio.TimeoutError:
                self.queue.put_nowait(request)
                await asyncio.sleep(timeout)
                retries -= 1

        raise ValueError

    def subscribe(self, name: str, callback: SensorCallbackType) -> None:
        """Subscribe a callback to the value change event."""
        if name not in self._callbacks:
            self._callbacks[name] = []

        self._callbacks[name].append(callback)

    def subscribe_once(self, name: str, callback: SensorCallbackType) -> None:
        """Subscribe a callback to the single value change event."""

        async def _callback(value):
            """Unregister the callback once it was called."""
            try:
                return await callback(value)
            finally:
                self.unsubscribe(name, _callback)

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

    def handle_frame(self, frame: Frame) -> None:
        """Handle received frame."""
        if frame.data is not None:
            for name, value in frame.data.items():
                self.set_device_data(name, value)


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
    """Represent the thermostat sub-device."""
