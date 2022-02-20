"""Contains classes for supported devices."""
from __future__ import annotations

from typing import Any, Dict, Final, List, Optional, Tuple

from .constants import (
    DATA_FRAMES,
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
MODE_STARTING: Final = 1
MODE_KINDLING: Final = 2
MODE_HEATING: Final = 3
MODE_SUPERVISION: Final = 4
MODE_COOLING: Final = 5
MODE_STANDBY: Final = 6
MODES: Final = (
    "Off",
    "Starting",
    "Kindling",
    "Heating",
    "Supervision",
    "Cooling",
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

        self._set_boiler_control_parameter()
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

    def _set_boiler_control_parameter(self):
        """Sets boiler control parameter from device data."""
        if not isinstance(self._parameters, Parameter):
            self._parameters[PARAM_BOILER_CONTROL] = Parameter(
                name=PARAM_BOILER_CONTROL, value=int(self.is_on), min_=0, max_=1
            )
        else:
            self._parameters[PARAM_BOILER_CONTROL].value = int(self.is_on)

    @property
    def software(self) -> Optional[str]:
        """Returns software version."""
        if MODULE_A in self._data:
            return self._data[MODULE_A]

        return None

    @property
    def is_on(self) -> bool:
        """Returns current state."""
        if DATA_MODE in self._data:
            return self._data[DATA_MODE] != MODE_OFF

        return False

    @property
    def mode(self) -> str:
        """Returns current mode."""
        if self._data and DATA_MODE in self._data:
            mode = self._data[DATA_MODE]
            try:
                return MODES[mode]
            except IndexError:
                pass

        return "Unknown"

    @property
    def changes(self) -> List[Request]:
        """Returns changed device parameters."""
        changes = self.queue
        changes.extend(self.bucket.queue)
        changes.extend(self.mixers.queue)
        return changes

    @property
    def editable_parameters(self) -> Tuple[str, ...]:
        """Returns list of editable parameters."""
        return DEVICE_PARAMS


class EcoMAX(Device):
    """ecoMAX device representation.

    Attributes:
        address -- device address
    """

    address = ECOMAX_ADDRESS


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
