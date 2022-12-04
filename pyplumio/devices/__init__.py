"""Contains device representations."""
from __future__ import annotations

from abc import ABC
import asyncio
from enum import IntEnum, unique
from typing import ClassVar, Dict, List, Optional

from pyplumio import util
from pyplumio.exceptions import ParameterNotFoundError, UnknownDeviceError
from pyplumio.frames import Frame
from pyplumio.helpers.parameter import Parameter
from pyplumio.helpers.task_manager import TaskManager
from pyplumio.helpers.typing import DeviceDataType, NumericType, SensorCallbackType


@unique
class DeviceTypes(IntEnum):
    """Contains device types."""

    ECOMAX = 69
    ECOSTER = 81


def _handler_class_path(device_type_name: str) -> str:
    """Return handler class path from device type name."""
    device_type_name = util.to_camelcase(
        device_type_name, overrides={"ecomax": "EcoMAX", "ecoster": "EcoSTER"}
    )
    return f"{device_type_name.lower()}.{device_type_name}"


# Dictionary of device handler classes indexed by device types.
# example: "69: ecomax.EcoMAX"
DEVICE_TYPES: Dict[int, str] = {
    device_type.value: _handler_class_path(device_type.name)
    for device_type in DeviceTypes
}


def get_device_handler(device_type: int) -> str:
    """Return module and class for device type."""
    if device_type in DEVICE_TYPES:
        return "devices." + DEVICE_TYPES[device_type]

    raise UnknownDeviceError(f"Unknown device ({device_type})")


class BaseDevice(ABC, TaskManager):
    """Represents base device with awaitable properties."""

    data: DeviceDataType
    _callbacks: Dict[str, List[SensorCallbackType]]

    def __init__(self):
        """Initializes Base Device object."""
        super().__init__()
        self.data = {}
        self._callbacks = {}

    async def get_value(self, name: str, timeout: Optional[float] = None):
        """Return a value. When encountering a parameter, only it's
        value will be returned. To return the Parameter object use
        get_parameter method."""
        if name not in self.data:
            await asyncio.wait_for(self.create_event(name).wait(), timeout=timeout)

        value = self.data[name]
        return int(value) if isinstance(value, Parameter) else value

    async def set_value(
        self,
        name: str,
        value: NumericType,
        timeout: Optional[float] = None,
        await_confirmation: bool = True,
    ) -> bool:
        """Set parameter value. Name should point
        to a valid parameter object."""
        if name not in self.data:
            await asyncio.wait_for(self.create_event(name).wait(), timeout=timeout)

        parameter = self.data[name]
        if not isinstance(parameter, Parameter):
            raise ParameterNotFoundError(f"Parameter not found ({name})")

        if await_confirmation:
            return await parameter.set(value)

        self.create_task(parameter.set(value))
        return True

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

    def set_device_data(self, *args, **kwargs) -> None:
        """Call registered callbacks on value change."""
        self.create_task(self.async_set_device_data(*args, **kwargs))

    async def async_set_device_data(self, name: str, value) -> None:
        """Asynchronously call registered callbacks on value change."""
        if name in self._callbacks:
            callbacks = self._callbacks[name].copy()
            for callback in callbacks:
                return_value = await callback(value)
                value = return_value if return_value is not None else value

        self.data[name] = value
        self.set_event(name)

    async def shutdown(self) -> None:
        """Cancel scheduled tasks."""
        self.cancel_tasks()
        await self.wait_until_done()

    def subscribe(self, name: str, callback: SensorCallbackType) -> None:
        """Register a callback for a value change."""
        if name not in self._callbacks:
            self._callbacks[name] = []

        self._callbacks[name].append(callback)

    def subscribe_once(self, name: str, callback: SensorCallbackType) -> None:
        """Register a callback for a single call."""

        async def _callback(value):
            """Unregister the callback once it was called."""
            try:
                return await callback(value)
            finally:
                self.unsubscribe(name, _callback)

        self.subscribe(name, _callback)

    def unsubscribe(self, name: str, callback: SensorCallbackType) -> None:
        """Remove the callback."""
        if name in self._callbacks and callback in self._callbacks[name]:
            self._callbacks[name].remove(callback)


class Device(BaseDevice):
    """Represents the addressable device."""

    address: ClassVar[int]
    queue: asyncio.Queue

    def __init__(self, queue: asyncio.Queue):
        """Initialize new Device object."""
        super().__init__()
        self.queue = queue

    def handle_frame(self, frame: Frame) -> None:
        """Handle received frame."""
        if frame.data is not None:
            for name, value in frame.data.items():
                self.set_device_data(name, value)


class Mixer(BaseDevice):
    """Represents the mixer device."""

    mixer_number: int

    def __init__(self, mixer_number: int = 0):
        """Initialize new Mixer object."""
        super().__init__()
        self.mixer_number = mixer_number
