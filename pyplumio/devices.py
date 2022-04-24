"""Contains classes for supported devices."""
from __future__ import annotations

import time
from typing import Any, Dict, Final, List, Optional

from .constants import (
    DATA_FRAMES,
    DATA_FUEL_CONSUMPTION,
    DATA_MODE,
    DEVICE_DATA,
    DEVICE_PARAMS,
    MODULE_A,
    PARAM_BOILER_CONTROL,
)
from .frame import Request
from .helpers.base_device import BaseDevice
from .helpers.parameter import Parameter
from .mixers import MixersCollection
from .storage import FrameBucket

ECOMAX_ADDRESS: Final = 0x45
ECOSTER_ADDRESS: Final = 0x51

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


class Device(BaseDevice):
    """Device representation.

    Attributes:
        bucket -- frame version info storage
        mixers -- collection of device mixers
        product -- device product type
        uid -- device uid string
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
        self.__dict__["bucket"] = FrameBucket()
        self.__dict__["mixers"] = MixersCollection(address=self.address)
        self.__dict__["product"] = None
        self.__dict__["uid"] = None
        self.__dict__["password"] = None
        self.__dict__["schema"] = []
        super().__init__(data, parameters)

    def __str__(self) -> str:
        """Converts device instance to a string."""
        return f"""
Product:        {self.product}
Software Ver.:  {self.software}
UID:            {self.uid}
Password:       {self.password}

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

        if DATA_FRAMES in data:
            self.bucket.fill(data[DATA_FRAMES])

    def set_parameters(self, parameters: Dict[str, List[int]]) -> None:
        """Sets device parameters.

        Keyword arguments:
            parameters -- device changeable parameters
        """
        for name, parameter in parameters.items():
            if name in DEVICE_PARAMS:
                self._parameters[name] = Parameter(name, *parameter)

    @property
    def is_on(self) -> bool:
        """Returns current state."""
        if DATA_MODE in self._data:
            return self._data[DATA_MODE] != MODE_OFF

        return False

    @property
    def software(self) -> Optional[str]:
        """Returns software version."""
        if MODULE_A in self._data:
            if self._data[MODULE_A] is not None:
                return self._data[MODULE_A]

            return "Unknown"

        return None

    @property
    def mode(self) -> Optional[str]:
        """Returns current mode."""
        if DATA_MODE in self._data:
            if self._data[DATA_MODE] < len(MODES):
                return MODES[self._data[DATA_MODE]]

            return "Unknown"

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
        parameters.extend(DEVICE_PARAMS)
        parameters.append(PARAM_BOILER_CONTROL)
        return parameters


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
        self.__dict__["_fuel_burned"] = 0.0
        self.__dict__["_fuel_burned_timestamp"] = time.time()
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
        if PARAM_BOILER_CONTROL in self._parameters and isinstance(
            self._parameters[PARAM_BOILER_CONTROL], Parameter
        ):
            self._parameters[PARAM_BOILER_CONTROL].value = int(self.is_on)
        else:
            self._parameters[PARAM_BOILER_CONTROL] = Parameter(
                name=PARAM_BOILER_CONTROL, value=int(self.is_on), min_=0, max_=1
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
