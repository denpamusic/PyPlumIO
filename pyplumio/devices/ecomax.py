"""Contains ecoMAX device representation."""
from __future__ import annotations

import asyncio
from collections.abc import Sequence
import time
from typing import ClassVar, List, Type

from pyplumio.const import (
    ATTR_BOILER_PARAMETERS,
    ATTR_BOILER_SENSORS,
    ATTR_FUEL_BURNED,
    ATTR_FUEL_CONSUMPTION,
    ATTR_MIXER_PARAMETERS,
    ATTR_MIXER_SENSORS,
    ATTR_MIXERS,
    ATTR_MODE,
    ATTR_REGDATA,
    ATTR_SCHEMA,
)
from pyplumio.devices import Device, DeviceTypes, Mixer
from pyplumio.frames import Request, requests
from pyplumio.helpers.data_types import Boolean
from pyplumio.helpers.filters import on_change
from pyplumio.helpers.parameter import (
    BoilerBinaryParameter,
    BoilerParameter,
    MixerBinaryParameter,
    MixerParameter,
    is_binary_parameter,
)
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures.boiler_parameters import PARAMETER_BOILER_CONTROL


class EcoMAX(Device):
    """Represents ecoMAX controller."""

    address: ClassVar[int] = DeviceTypes.ECOMAX
    _fuel_burned_timestamp: float = 0.0
    _required_frames: List[Type[Request]] = [
        requests.UIDRequest,
        requests.DataSchemaRequest,
        requests.BoilerParametersRequest,
        requests.MixerParametersRequest,
        requests.PasswordRequest,
        requests.AlertsRequest,
    ]

    def __init__(self, queue: asyncio.Queue):
        """Initialize new ecoMAX object."""
        super().__init__(queue)
        self._fuel_burned_timestamp = time.time()
        self.register_callback(ATTR_BOILER_SENSORS, self._add_boiler_sensors)
        self.register_callback(ATTR_MODE, on_change(self._add_boiler_control_parameter))
        self.register_callback(ATTR_FUEL_CONSUMPTION, self._add_burned_fuel_counter)
        self.register_callback(ATTR_BOILER_PARAMETERS, self._add_boiler_parameters)
        self.register_callback(ATTR_REGDATA, self._decode_regulator_data)
        self.register_callback(ATTR_MIXER_SENSORS, self._set_mixer_sensors)
        self.register_callback(ATTR_MIXER_PARAMETERS, self._set_mixer_parameters)

    def _get_mixer(self, mixer_number: int, total_mixers: int) -> Mixer:
        """Get or create a new mixer object and add it to the device."""
        mixers = self.data.setdefault(ATTR_MIXERS, [])
        try:
            mixer = mixers[mixer_number]
        except IndexError:
            mixer = Mixer(mixer_number)
            mixers.append(mixer)
            if len(mixers) == total_mixers:
                # All mixers were processed, notify callbacks and getters.
                self.set_device_data(ATTR_MIXERS, mixers)

        return mixer

    async def _add_boiler_sensors(self, sensors: DeviceDataType) -> bool:
        """Add boiler sensors values to the device data."""
        for name, value in sensors.items():
            await self.async_set_device_data(name, value)

        return True

    async def _add_boiler_parameters(self, parameters: DeviceDataType) -> bool:
        """Add Parameter objects to the device data."""
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
            await self.async_set_device_data(name, parameter)

        return True

    async def _set_mixer_sensors(self, sensors: Sequence[DeviceDataType]) -> bool:
        """Set sensor values for the mixer."""
        for mixer_number, mixer_data in enumerate(sensors):
            mixer = self._get_mixer(mixer_number, len(sensors))
            for name, value in mixer_data.items():
                await mixer.async_set_device_data(name, value)

        return True

    async def _set_mixer_parameters(self, parameters: Sequence[DeviceDataType]) -> bool:
        """Set mixer parameters."""
        for mixer_number, mixer_data in enumerate(parameters):
            mixer = self._get_mixer(mixer_number, len(parameters))
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
                await mixer.async_set_device_data(name, parameter)

        return True

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
        await self.async_set_device_data(PARAMETER_BOILER_CONTROL, parameter)

    async def _add_burned_fuel_counter(self, fuel_consumption: int) -> None:
        """Add burned fuel counter."""
        current_timestamp = time.time()
        seconds_passed = current_timestamp - self._fuel_burned_timestamp
        fuel_burned = (fuel_consumption / 3600) * seconds_passed
        self._fuel_burned_timestamp = current_timestamp
        await self.async_set_device_data(ATTR_FUEL_BURNED, fuel_burned)

    async def _decode_regulator_data(self, regulator_data: bytes) -> DeviceDataType:
        """Add sensor values from the regulator data."""
        offset = 0
        boolean_index = 0
        regdata: DeviceDataType = {}
        schema = self.data.get(ATTR_SCHEMA, [])
        for parameter in schema:
            parameter_id, parameter_type = parameter
            if not isinstance(parameter_type, Boolean) and boolean_index > 0:
                offset += 1
                boolean_index = 0

            parameter_type.unpack(regulator_data[offset:])
            if isinstance(parameter_type, Boolean):
                boolean_index = parameter_type.index(boolean_index)

            regdata[parameter_id] = parameter_type.value
            offset += parameter_type.size

        return regdata

    async def shutdown(self) -> None:
        """Cancel scheduled tasks."""
        mixers = self.data.get(ATTR_MIXERS, [])
        for mixer in mixers:
            await mixer.shutdown()

        await super().shutdown()
