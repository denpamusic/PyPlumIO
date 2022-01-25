"""Contains classes for supported devices."""
from __future__ import annotations

from .constants import (
    CURRENT_DATA,
    DATA_FRAMES,
    DATA_MODE,
    EDITABLE_PARAMS,
    MODES,
    MODULE_PANEL,
)
from .helpers.base_device import BaseDevice
from .helpers.parameter import Parameter
from .mixers import MixersCollection
from .storage import FrameBucket

ECOMAX_ADDRESS: int = 0x45
ECOSTER_ADDRESS: int = 0x51


class Device(BaseDevice):
    """A device representation.

    Passed to the user-defined callback method.
    """

    def __init__(self, data: dict = None, parameters: dict = None):
        """Creates device instance.

        Keyword arguments:
        data -- device data
        parameters -- editable parameters
        """
        super().__init__(data, parameters)
        self.product = None
        self.uid = None
        self.password = None
        self.struct = []
        self.bucket = FrameBucket()
        self.mixers = MixersCollection()
        self._queue = []
        self._is_on = False

    def set_data(self, data: dict) -> None:
        """Sets device data.

        Keyword arguments:
        data -- device immutable attributes
        """
        self.bucket.fill(data[DATA_FRAMES])
        for name, value in data.items():
            if name in CURRENT_DATA:
                self._data[name] = value

    def set_parameters(self, parameters: dict) -> None:
        """Sets device parameters.

        Keyword arguments:
        parameters -- device changeable parameters
        """
        for name, parameter in parameters.items():
            if name in EDITABLE_PARAMS:
                self._parameters[name] = Parameter(name, *parameter)

        self._parameters["BOILER_CONTROL"] = Parameter(
            name="BOILER_CONTROL", value=int(self.is_on), min_=0, max_=1
        )

    def has_mixers(self) -> bool:
        """Check if device instance has mixers."""
        return bool(self.mixers.mixers)

    @property
    def software(self) -> str:
        """Returns software version."""
        try:
            return self._data[MODULE_PANEL]
        except KeyError:
            return None

    @property
    def is_on(self) -> bool:
        """Returns current state."""
        try:
            return bool(self._data[DATA_MODE] != 0)
        except KeyError:
            return False

    @property
    def mode(self) -> str:
        """Returns current mode."""
        if self._data:
            mode = self._data[DATA_MODE]
            try:
                return MODES[mode]
            except IndexError:
                pass

        return "Unknown"

    @property
    def changes(self) -> list[Parameter]:
        """Returns changed device parameters."""
        changes = self.queue
        changes.extend(self.bucket.queue)
        changes.extend(self.mixers.queue)
        return changes

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


class EcoMAX(Device):
    """ecoMAX device representation."""

    address = ECOMAX_ADDRESS


class EcoSTER(Device):
    """ecoSTER device representation."""

    address = ECOSTER_ADDRESS


class DevicesCollection:
    """Collection of ecoNET devices."""

    def __init__(self):
        """Creates device collection."""
        self._classes = Device.__subclasses__()
        self._addresses = [v.address for v in self._classes]
        self._instances = {}
        self._names = {}

    def __getattr__(self, name: str) -> Device | None:
        """Gets device by name.""

        Keyword arguments:
        name -- name of device to get
        """
        name = name.lower()
        if name in self._names:
            return self._instances[self._names[name]]

        return None

    def __len__(self) -> int:
        """Returns number of devices in collection."""
        return len(self._instances)

    def has(self, needle) -> bool:
        """Checks if collection has device for specified address.

        Keyword arguments:
        needle -- address or name of device
        """
        return (needle in self._addresses) or (needle in self._names)

    def get(self, address: int) -> Device | None:
        """Gets device by address.

        Keyword arguments:
        address -- int address of device
        """
        if address not in self._instances:
            try:
                index = self._addresses.index(address)
                cls = self._classes[index]
            except KeyError:
                return None

            self._instances[address] = cls()
            self._names[cls.__name__.lower()] = address

        return self._instances[address]
