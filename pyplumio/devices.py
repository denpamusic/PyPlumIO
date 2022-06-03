"""Contains classes for supported devices."""
from __future__ import annotations

from abc import abstractmethod
import time
from typing import Any, Dict, Final, List, Optional, Tuple, Type

from .constants import (
    DATA_FAN_POWER,
    DATA_FUEL_CONSUMPTION,
    DATA_FUEL_LEVEL,
    DATA_LOAD,
    DATA_MODE,
    DATA_POWER,
    DATA_THERMOSTAT,
    DATA_TRANSMISSION,
    DATA_UNKNOWN,
    ECOMAX_ADDRESS,
    ECOSTER_ADDRESS,
)
from .data_types import DataType
from .frames import Request, requests
from .helpers.base_device import BaseDevice
from .helpers.parameter import Parameter
from .helpers.product_info import ConnectedModules, ProductInfo
from .mixers import MixersCollection
from .storage import FrameBucket
from .structures import (
    alarms,
    device_parameters,
    frame_versions,
    lambda_,
    output_flags,
    outputs,
    statuses,
    temperatures,
    thermostats,
)

MODE_OFF: Final = 0
MODE_FANNING: Final = 1
MODE_KINDLING: Final = 2
MODE_HEATING: Final = 3
MODE_SUSTAIN: Final = 4
MODE_IDLE: Final = 5
MODE_STANDBY: Final = 6
MODES: Final = (
    "Off",
    "Fanning",
    "Kindling",
    "Heating",
    "Sustain",
    "Idle",
    "Standby",
)

DEVICE_DATA: List[str] = [
    DATA_FAN_POWER,
    DATA_FUEL_CONSUMPTION,
    DATA_FUEL_LEVEL,
    DATA_LOAD,
    DATA_MODE,
    DATA_POWER,
    DATA_THERMOSTAT,
    DATA_TRANSMISSION,
]
DEVICE_DATA.extend(alarms.ALARMS)
DEVICE_DATA.extend(frame_versions.FRAME_VERSIONS)
DEVICE_DATA.extend(temperatures.TEMPERATURES)
DEVICE_DATA.extend(outputs.OUTPUTS)
DEVICE_DATA.extend(output_flags.OUTPUT_FLAGS)
DEVICE_DATA.extend(statuses.STATUSES)
DEVICE_DATA.extend(lambda_.LAMBDA)
DEVICE_DATA.extend(thermostats.THERMOSTATS)


class Device(BaseDevice):
    """Device representation.

    Attributes:
        bucket -- frame version info storage
        mixers -- collection of device mixers
        product -- device product info
        password -- device service password
        schema -- device regdata schema
    """

    def __init__(
        self, data: Dict[str, Any] = None, parameters: Dict[str, List[int]] = None
    ):
        """Creates device instance.

        Keyword arguments:
            data -- device data
            parameters -- editable parameters
        """
        self.bucket = FrameBucket(address=self.address, required=self.required_frames)
        self.mixers = MixersCollection(address=self.address)
        self.product = ProductInfo()
        self.modules = ConnectedModules()
        self.password = None
        self.schema: List[Tuple[str, DataType]] = []
        super().__init__(data, parameters)

    def __str__(self) -> str:
        """Converts device instance to a string."""
        return f"""
Model:     {self.product.model}
UID:       {self.product.uid}
Password:  {self.password}
Modules:   {self.modules}

{super().__str__()}

Mixers:
{self.mixers}
""".strip()

    def set_data(self, data: Dict[str, Any]) -> None:
        """Sets device data.

        Keyword arguments:
            data -- immutable device attributes
        """
        for name, value in data.items():
            if name in DEVICE_DATA:
                self._data[name] = value

        if frame_versions.FRAME_VERSIONS in data:
            self.bucket.fill(data[frame_versions.FRAME_VERSIONS])

    def set_parameters(self, parameters: Dict[str, List[int]]) -> None:
        """Sets device parameters.

        Keyword arguments:
            parameters -- device changeable parameters
        """
        for name, parameter in parameters.items():
            if name in device_parameters.DEVICE_PARAMETERS:
                self._parameters[name] = Parameter(name, *parameter)

    @property
    def is_on(self) -> bool:
        """Returns current state."""
        if DATA_MODE in self._data:
            return self._data[DATA_MODE] != MODE_OFF

        return False

    @property
    def mode(self) -> Optional[str]:
        """Returns current mode."""
        if DATA_MODE in self._data:
            if self._data[DATA_MODE] < len(MODES):
                return MODES[self._data[DATA_MODE]]

            return DATA_UNKNOWN

        return None

    @property
    def changes(self) -> List[Request]:
        """Returns changed device parameters."""
        changes = self.queue
        changes.extend(self.bucket.queue)
        changes.extend(self.mixers.queue)
        return changes

    @property
    def editable_parameters(self) -> List[str]:
        """Returns list of editable parameters."""
        parameters: List[str] = []
        parameters.extend(device_parameters.DEVICE_PARAMETERS)
        return parameters

    @property
    @abstractmethod
    def required_frames(self) -> Tuple[Type[Request], ...]:
        """Returns tuple of required frames."""


class EcoMAX(Device):
    """ecoMAX device representation.

    Attributes:
        address -- device address
        _fuel_burned -- amount of fuel burned in kilograms
        _fuel_burned_timestamp -- timestamp of burned fuel value update
    """

    address = ECOMAX_ADDRESS
    _fuel_burned: float = 0.0
    _fuel_burned_timestamp: float = 0.0

    def __init__(
        self, data: Dict[str, Any] = None, parameters: Dict[str, List[int]] = None
    ):
        """Creates device instance.

        Keyword arguments:
            data -- device data
            parameters -- editable parameters
        """
        self._fuel_burned = 0.0
        self._fuel_burned_timestamp = time.time()
        super().__init__(data, parameters)

    def set_data(self, data: Dict[str, Any]) -> None:
        """Sets device data.

        Keyword arguments:
            data -- immutable device attributes
        """
        if DATA_FUEL_CONSUMPTION in data:
            self._set_fuel_burned(data[DATA_FUEL_CONSUMPTION])

        self._set_boiler_control_parameter()
        super().set_data(data)

    def _set_boiler_control_parameter(self):
        """Sets boiler control parameter from device data."""
        if (
            device_parameters.PARAMETER_BOILER_CONTROL in self._parameters
            and isinstance(
                self._parameters[device_parameters.PARAMETER_BOILER_CONTROL], Parameter
            )
        ):
            self._parameters[device_parameters.PARAMETER_BOILER_CONTROL].value = int(
                self.is_on
            )
        else:
            self._parameters[device_parameters.PARAMETER_BOILER_CONTROL] = Parameter(
                name=device_parameters.PARAMETER_BOILER_CONTROL,
                value=int(self.is_on),
                min_value=0,
                max_value=1,
            )

    def _set_fuel_burned(self, fuel_consumption: float) -> None:
        """Sets amount of fuel burned since last message.

        Keyword arguments:
            fuel_consumption -- fuel flow in kg/h
        """
        current_timestamp = time.time()
        seconds_passed = current_timestamp - self._fuel_burned_timestamp
        self._fuel_burned += (fuel_consumption / 3600) * seconds_passed
        self._fuel_burned_timestamp = current_timestamp

    @property
    def fuel_burned(self) -> float:
        """Returns amount of fuel burned and resets counter."""
        fuel_burned = self._fuel_burned
        self._fuel_burned = 0
        return fuel_burned

    @property
    def required_frames(self) -> Tuple[Type[Request], ...]:
        """Returns tuple of required frames."""
        return (
            requests.UID,
            requests.Password,
            requests.BoilerParameters,
            requests.MixerParameters,
        )

    @property
    def editable_parameters(self) -> List[str]:
        """Returns list of editable parameters."""
        parameters = super().editable_parameters
        parameters.append(device_parameters.PARAMETER_BOILER_CONTROL)
        return parameters


class EcoSTER(Device):
    """ecoSTER device representation.

    Attributes:
        address -- device address
    """

    address = ECOSTER_ADDRESS


class DevicesCollection:
    """Collection of devices.

    Attributes:
        _classes -- device handler class names
        _addresses -- device classes mapped with device addresses
        _instances -- device handler instances
        _name -- device instances mapped with lowecased class names
    """

    def __init__(self):
        """Creates device collection."""
        self._classes = Device.__subclasses__()
        self._addresses = [v.address for v in self._classes]
        self._instances = {}
        self._names = {}

    def __getattr__(self, name: str) -> Optional[Device]:
        """Gets device by name.""

        Keyword arguments:
            name -- name of device to get
        """
        name = name.lower()
        if name in self._names:
            return self._instances[self._names[name]]

        raise AttributeError

    def __len__(self) -> int:
        """Returns number of devices in collection."""
        return len(self._instances)

    def has(self, needle) -> bool:
        """Checks if collection has device for specified address.

        Keyword arguments:
            needle -- address or name of device
        """
        return (needle in self._addresses) or (needle in self._names)

    def get(self, address: int) -> Optional[Device]:
        """Gets device by address.

        Keyword arguments:
            address -- address of device
        """
        if address not in self._instances:
            try:
                index = self._addresses.index(address)
                cls = self._classes[index]
            except ValueError:
                return None

            self._instances[address] = cls()
            self._names[cls.__name__.lower()] = address

        return self._instances[address]
