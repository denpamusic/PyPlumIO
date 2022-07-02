"""Contains device representations."""
from __future__ import annotations

from abc import ABC
import asyncio
from collections.abc import Mapping, MutableMapping, MutableSequence, Sequence
import time
from typing import Type

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
from pyplumio.exceptions import (
    ParameterNotFoundError,
    UnknownDeviceError,
    UnknownFrameError,
)
from pyplumio.frames import Frame, Request, get_frame_handler, requests
from pyplumio.helpers.data_types import Boolean
from pyplumio.helpers.factory import factory
from pyplumio.helpers.parameter import (
    BoilerBinaryParameter,
    BoilerParameter,
    MixerBinaryParameter,
    MixerParameter,
    Parameter,
    is_binary_parameter,
)
from pyplumio.helpers.timeout import timeout
from pyplumio.helpers.typing import (
    Numeric,
    Parameters,
    ParameterTuple,
    Records,
    ValueCallback,
)
from pyplumio.structures.boiler_parameters import PARAMETER_BOILER_CONTROL

devices: Mapping[int, str] = {
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

    versions: MutableMapping[int, int]
    _queue: asyncio.Queue
    _device: Device
    _required_frames: MutableMapping[int, int]

    def __init__(self, queue: asyncio.Queue, device: Device):
        """Initialize Frame Versions object."""
        self.versions = {}
        self._queue = queue
        self._device = device
        self._required_frames = {x.frame_type: 0 for x in device.required_frames}

    async def update(self, frame_versions: MutableMapping[int, int]) -> None:
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


def _significantly_changed(old_value, new_value) -> bool:
    """Check if value is significantly changed."""
    if isinstance(old_value, float) and isinstance(new_value, float):
        return round(old_value, 1) != round(new_value, 1)

    return old_value != new_value


class AsyncDevice(ABC):
    """Represents a device with awaitable properties."""

    _callbacks: MutableMapping[str, MutableSequence[ValueCallback]]

    def __init__(self):
        self._callbacks = {}

    @timeout(VALUE_TIMEOUT)
    async def get_value(self, name: str):
        """Return a value. When encountering a parameter, only it's
        value will be returned. To return the Parameter object use
        get_parameter(name: str) method."""
        while not hasattr(self, name):
            await asyncio.sleep(0)

        value = getattr(self, name)
        return int(value) if isinstance(value, Parameter) else value

    @timeout(VALUE_TIMEOUT)
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

    @timeout(VALUE_TIMEOUT)
    async def get_parameter(self, name: str) -> Parameter:
        """Return a parameter."""
        while not hasattr(self, name):
            await asyncio.sleep(0)

        parameter = getattr(self, name)
        if isinstance(parameter, Parameter):
            return parameter

        raise ParameterNotFoundError(f"parameter {name} not found")

    async def async_set_attribute(
        self, name: str, value, skip_change_check: bool = False
    ) -> None:
        """Call registered callbacks on value change."""
        old_value = self.__dict__[name] if name in self.__dict__ else None
        if name in self._callbacks and (
            skip_change_check or _significantly_changed(old_value, value)
        ):
            for callback in self._callbacks[name]:
                return_value = await callback(value)
                value = return_value if return_value is not None else value

        self.__dict__[name] = value

    def register_callback(self, sensors: Sequence[str], callback: ValueCallback):
        """Register callback for sensor change."""
        for sensor in sensors:
            if sensor not in self._callbacks:
                self._callbacks[sensor] = []

            self._callbacks[sensor].append(callback)

    def remove_callback(self, sensors: Sequence[str], callback: ValueCallback):
        """Remove callback for sensor change."""
        for sensor in sensors:
            if sensor in self._callbacks and callback in self._callbacks[sensor]:
                self._callbacks[sensor].remove(callback)


class Mixer(AsyncDevice):
    """Represents mixer device."""

    def __init__(self, index: int = 0):
        """Initialize new Mixer object."""
        super().__init__()
        self.index = index


class Device(AsyncDevice):
    """Represents base device."""

    address: int = BROADCAST_ADDRESS
    _queue: asyncio.Queue
    _required_frames: Sequence[Type[Request]] = []

    def __init__(self, queue: asyncio.Queue):
        """Initialize new Device object."""
        super().__init__()
        self._queue = queue
        versions = FrameVersions(queue, device=self)
        self.register_callback([DATA_FRAME_VERSIONS], versions.update)

    async def handle_frame(self, frame: Frame) -> None:
        """Handle received frame."""
        if frame.data is not None:
            for name, value in frame.data.items():
                await self.async_set_attribute(name, value)

    @property
    def required_frames(self) -> Sequence[Type[Request]]:
        """Return list of required frames."""
        return self._required_frames

    @property
    def queue(self) -> asyncio.Queue:
        """Return device write queue."""
        return self._queue


class EcoMAX(Device):
    """Represents ecoMAX controller."""

    address: int = ECOMAX_ADDRESS
    mixers: MutableMapping[int, Mixer] = {}
    _fuel_burned_timestamp: float = 0.0
    _required_frames: Sequence[Type[Request]] = [
        requests.UID,
        requests.Password,
        requests.DataSchema,
        requests.BoilerParameters,
        requests.MixerParameters,
    ]

    def __init__(self, queue: asyncio.Queue):
        """Initialize new ecoMAX object."""
        super().__init__(queue)
        self._mixers: MutableMapping[int, Mixer] = {}
        self._fuel_burned_timestamp = time.time()
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

    async def _add_boiler_sensors(self, sensors: Records):
        """Add boiler sensors values to the device object."""
        for name, value in sensors.items():
            await self.async_set_attribute(name, value)

    async def _add_boiler_parameters(
        self, parameters: Parameters
    ) -> MutableMapping[str, Parameter]:
        """Add Parameter objects to the device object."""
        parameter_objects: MutableMapping[str, Parameter] = {}
        for name, value in parameters.items():
            cls = (
                BoilerBinaryParameter if is_binary_parameter(value) else BoilerParameter
            )
            parameter = cls(
                self._queue,
                self.address,
                name,
                value=value[0],
                min_value=value[1],
                max_value=value[2],
            )
            await self.async_set_attribute(name, parameter)
            parameter_objects[name] = parameter

        return parameter_objects

    async def _set_mixer_sensors(
        self, sensors: Sequence[MutableMapping[str, Records]]
    ) -> None:
        """Set sensor values for the mixer."""
        for mixer_number, mixer_data in enumerate(sensors):
            mixer = self._get_mixer(mixer_number)
            for name, value in mixer_data.items():
                await mixer.async_set_attribute(name, value)

    async def _set_mixer_parameters(
        self, parameters: Sequence[MutableMapping[str, ParameterTuple]]
    ) -> None:
        """Set mixer parameters."""
        for mixer_number, mixer_data in enumerate(parameters):
            mixer = self._get_mixer(mixer_number)
            for name, value in mixer_data.items():
                cls = (
                    MixerBinaryParameter
                    if is_binary_parameter(value)
                    else MixerParameter
                )
                parameter = cls(
                    queue=self._queue,
                    recipient=self.address,
                    name=name,
                    value=value[0],
                    min_value=value[1],
                    max_value=value[2],
                    extra=mixer_number,
                )
                await mixer.async_set_attribute(name, parameter)

    async def _add_boiler_control_parameter(self, mode: int) -> None:
        """Add BoilerControl parameter to the device instance."""
        parameter = BoilerBinaryParameter(
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
        fuel_burned = (fuel_consumption / 3600) * seconds_passed
        self._fuel_burned_timestamp = current_timestamp
        await self.async_set_attribute(
            "fuel_burned", fuel_burned, skip_change_check=True
        )

    async def _parse_regulator_data(self, regulator_data: bytes) -> Records:
        """Add sensor values from the regulator data."""
        offset = 0
        boolean_index = 0
        data = {}
        try:
            schema = await self.get_value(DATA_SCHEMA)
            for parameter in schema:
                parameter_id, parameter_type = parameter
                if not isinstance(parameter_type, Boolean) and boolean_index > 0:
                    offset += 1
                    boolean_index = 0

                parameter_type.unpack(regulator_data[offset:])
                if isinstance(parameter_type, Boolean):
                    boolean_index = parameter_type.index(boolean_index)

                data[parameter_id] = parameter_type.value
                offset += parameter_type.size
        except asyncio.TimeoutError:
            # Return empty dictionary on exception.
            pass

        return data


class EcoSTER(Device):
    """Represents ecoSTER thermostat."""

    address: int = ECOSTER_ADDRESS
