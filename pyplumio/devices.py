"""Contains device representations."""
from __future__ import annotations

from abc import ABC
import asyncio
from collections.abc import Iterable
import time
from typing import Any, Dict, List, Set, Type

from pyplumio.const import (
    BROADCAST_ADDRESS,
    DATA_BOILER_PARAMETERS,
    DATA_BOILER_SENSORS,
    DATA_FRAME_VERSIONS,
    DATA_FUEL_CONSUMPTION,
    DATA_MIXER_PARAMETERS,
    DATA_MIXER_SENSORS,
    DATA_MODE,
    DATA_REGDATA,
    DATA_SCHEMA,
    ECOMAX_ADDRESS,
    ECOSTER_ADDRESS,
)
from pyplumio.data_types import Boolean
from pyplumio.exceptions import (
    ParameterNotFoundError,
    UnknownDeviceError,
    UnknownFrameError,
)
from pyplumio.frames import Frame, Request, get_frame_handler, requests
from pyplumio.helpers.classname import ClassName
from pyplumio.helpers.factory import factory
from pyplumio.helpers.parameter import BoilerParameter, MixerParameter, Parameter
from pyplumio.helpers.timeout import timeout
from pyplumio.structures.boiler_parameters import PARAMETER_BOILER_CONTROL
from pyplumio.typing import AsyncCallback, Numeric, ParameterTuple

devices: Dict[int, str] = {
    ECOMAX_ADDRESS: "EcoMAX",
    ECOSTER_ADDRESS: "EcoSTER",
}


VALUE_TIMEOUT: int = 5


def get_device_handler(address: int) -> str:
    """Return module and class for device address."""
    if address in devices:
        return "devices." + devices[address]

    raise UnknownDeviceError(f"Unknown device: {address}")


class FrameVersions:
    """Represents frame versions storage."""

    versions: Dict[int, int]
    _queue: asyncio.Queue
    _device: Device
    _required_frames: Dict[int, int]

    def __init__(self, queue: asyncio.Queue, device: Device):
        """Initialize Frame Versions object."""
        self.versions = {}
        self._queue = queue
        self._device = device
        self._required_frames = {x.frame_type: 0 for x in device.required_frames}

    async def update(self, frame_versions: Dict[int, int]) -> None:
        """Check frame versions and fetch outdated frames."""
        frame_versions = {**frame_versions, **self._required_frames}
        for frame_type, version in frame_versions.items():
            if frame_type not in self.versions or self.versions[frame_type] != version:
                # We don't have this frame or it's version has changed.
                try:
                    request = factory(
                        get_frame_handler(frame_type), recipient=self._device.address
                    )
                    self._queue.put_nowait(request)
                    self.versions[frame_type] = version
                except UnknownFrameError:
                    # Ignore unknown frames in version list.
                    continue


class AsyncDevice:
    """Represents a device with awaitable properties."""

    _callbacks: Dict[str, List[AsyncCallback]]

    def __init__(self):
        """Initialize new Device object."""
        self._callbacks = {}

    @timeout(VALUE_TIMEOUT, raise_exception=False)
    async def get_value(self, name: str) -> Any:
        """Return a value. When encountering a parameter, only it's
        value will be returned. To return the Parameter object use
        get_parameter(name: str) method."""
        while not hasattr(self, name):
            await asyncio.sleep(0)

        value = getattr(self, name)
        return int(value) if isinstance(value, Parameter) else value

    @timeout(VALUE_TIMEOUT, raise_exception=False)
    async def set_value(self, name: str, value: Numeric) -> None:
        """Set parameter value. Name should point
        to a valid parameter object."""
        while not hasattr(self, name):
            await asyncio.sleep(0)

        parameter = getattr(self, name)
        if isinstance(parameter, Parameter):
            parameter.set(value)
            return

        raise ParameterNotFoundError(f"parameter {name} not found")

    @timeout(VALUE_TIMEOUT, raise_exception=False)
    async def get_parameter(self, name: str) -> Parameter:
        """Return a parameter."""
        while not hasattr(self, name):
            await asyncio.sleep(0)

        parameter = getattr(self, name)
        if isinstance(parameter, Parameter):
            return parameter

        raise ParameterNotFoundError(f"parameter {name} not found")

    async def async_set_attribute(self, name: str, value: Any) -> None:
        """Call registered callbacks on setattr call."""
        if name in self._callbacks:
            for callback in self._callbacks[name]:
                return_value = await callback(value)
                value = return_value if return_value is not None else value

        self.__dict__[name] = value

    def register_callback(self, sensors: Iterable[str], callback: AsyncCallback):
        """Register callback for sensor change."""
        for sensor in sensors:
            if sensor not in self._callbacks:
                self._callbacks[sensor] = []

            self._callbacks[sensor].append(callback)

    def remove_callback(self, sensors: Iterable[str], callback: AsyncCallback):
        """Remove callback for sensor change."""
        for sensor in sensors:
            if sensor in self._callbacks and callback in self._callbacks[sensor]:
                self._callbacks[sensor].remove(callback)


class Mixer(AsyncDevice):
    """Represents mixer device."""

    def __init__(self, index: int = 0):
        """Initialize new Mixer object."""
        AsyncDevice.__init__(self)
        self.index = index


class Device(ABC, AsyncDevice, ClassName):
    """Represents base device."""

    address: int = BROADCAST_ADDRESS
    _queue: asyncio.Queue
    _tasks: Set[asyncio.Task]
    _required_frames: Iterable[Type[Request]] = []

    def __init__(self, queue: asyncio.Queue):
        """Initialize new Device object."""
        AsyncDevice.__init__(self)
        self._queue = queue
        self._tasks = set()
        versions = FrameVersions(queue, device=self)
        self.register_callback([DATA_FRAME_VERSIONS], versions.update)

    async def handle_frame(self, frame: Frame) -> None:
        """Handle received frame."""
        if frame.data is not None:
            for name, value in frame.data.items():
                task = asyncio.create_task(self.async_set_attribute(name, value))
                self._tasks.add(task)
                task.add_done_callback(self._tasks.discard)

    @property
    def required_frames(self) -> Iterable[Type[Request]]:
        """Return list of required frames."""
        return self._required_frames


class EcoMAX(Device):
    """Represents ecoMAX controller."""

    address: int = ECOMAX_ADDRESS
    mixers: Dict[int, Mixer] = {}
    _fuel_burned: float = 0.0
    _fuel_burned_timestamp: float = 0.0
    _required_frames: Iterable[Type[Request]] = [
        requests.UID,
        requests.Password,
        requests.DataSchema,
        requests.BoilerParameters,
        requests.MixerParameters,
    ]

    def __init__(self, queue: asyncio.Queue):
        """Initialize new ecoMAX object."""
        super().__init__(queue)
        self._mixers: Dict[int, Mixer] = {}
        self._fuel_burned = 0.0
        self._fuel_burned_timestamp = 0.0
        self.register_callback([DATA_BOILER_SENSORS], self._add_boiler_sensors)
        self.register_callback([DATA_MODE], self._add_boiler_control_parameter)
        self.register_callback([DATA_FUEL_CONSUMPTION], self._add_burned_fuel_counter)
        self.register_callback([DATA_BOILER_PARAMETERS], self._add_boiler_parameters)
        self.register_callback([DATA_REGDATA], self._parse_regulator_data)
        self.register_callback([DATA_MIXER_SENSORS], self._set_mixer_sensors)
        self.register_callback([DATA_MIXER_PARAMETERS], self._set_mixer_parameters)

    def _get_mixer(self, mixer_number: int) -> Mixer:
        """Get or create a new mixer object and add it to the device."""
        mixer = (
            self.mixers[mixer_number]
            if mixer_number in self.mixers
            else Mixer(mixer_number)
        )
        self.mixers[mixer_number] = mixer
        return mixer

    def reset_burned_fuel(self):
        """Reset burned fuel counter."""
        self._fuel_burned = 0.0
        self._fuel_burned_timestamp = time.time()

    async def _add_boiler_sensors(self, sensors: Dict[str, Any]):
        """Add boiler sensors values to the device object."""
        for name, value in sensors.items():
            await self.async_set_attribute(name, value)

    async def _add_boiler_parameters(
        self, parameters: Dict[str, ParameterTuple]
    ) -> Dict[str, Parameter]:
        """Add Parameter objects to the device object."""
        parameter_objects: Dict[str, Parameter] = {}
        for name, value in parameters.items():
            parameter = BoilerParameter(self._queue, self.address, *value)
            await self.async_set_attribute(name, parameter)
            parameter_objects[name] = parameter

        return parameter_objects

    async def _set_mixer_sensors(
        self, sensors: List[Dict[str, Dict[str, Any]]]
    ) -> None:
        """Set sensor values for the mixer."""
        for mixer_number, mixer_data in enumerate(sensors):
            mixer = self._get_mixer(mixer_number)
            for name, value in mixer_data.items():
                await mixer.async_set_attribute(name, value)

    async def _set_mixer_parameters(
        self, parameters: List[Dict[str, ParameterTuple]]
    ) -> None:
        """Set mixer parameters."""
        for mixer_number, mixer_data in enumerate(parameters):
            mixer = self._get_mixer(mixer_number)
            for name, value in mixer_data.items():
                parameter = MixerParameter(
                    queue=self._queue,
                    recipient=self.address,
                    name=name,
                    value=value[1],
                    min_value=value[2],
                    max_value=value[3],
                    extra=mixer_number,
                )
                await mixer.async_set_attribute(name, parameter)

    async def _add_boiler_control_parameter(self, mode: int) -> None:
        """Add BoilerControl parameter to the device instance."""
        parameter = BoilerParameter(
            queue=self._queue,
            recipient=self.address,
            name=PARAMETER_BOILER_CONTROL,
            value=(mode != 0),
            min_value=0,
            max_value=1,
        )
        await self.async_set_attribute(PARAMETER_BOILER_CONTROL, parameter)

    async def _add_burned_fuel_counter(self, fuel_consumption: int) -> None:
        """Add burned fuel counter."""
        current_timestamp = time.time()
        seconds_passed = current_timestamp - self._fuel_burned_timestamp
        self._fuel_burned += (fuel_consumption / 3600) * seconds_passed
        self._fuel_burned_timestamp = current_timestamp

    async def _parse_regulator_data(self, regulator_data: bytes):
        """Add sensor values from the regulator data."""
        offset = 0
        boolean_index = 0
        data = {}
        schema = await self.get_value(DATA_SCHEMA)
        for param in schema:
            param_id, param_type = param
            if not isinstance(param_type, Boolean) and boolean_index > 0:
                offset += 1
                boolean_index = 0

            param_type.unpack(regulator_data[offset:])
            if isinstance(param_type, Boolean):
                boolean_index = param_type.index(boolean_index)

            data[param_id] = param_type.value
            offset += param_type.size

        return data

    @property
    def fuel_burned(self):
        """Return amount of fuel burned since connection start."""
        return self._fuel_burned


class EcoSTER(Device):
    """Represents ecoSTER thermostat."""

    address: int = ECOSTER_ADDRESS
