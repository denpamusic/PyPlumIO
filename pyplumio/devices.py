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
from .frame import Request
from .frames.requests import BoilerControl, SetParameter
from .storage import FrameBucket

ECOMAX_ADDRESS: int = 0x45
ECOSTER_ADDRESS: int = 0x51


class Device:
    """A device representation.

    Passed to the user-defined callback method.
    """

    def __init__(self, data: dict = None, parameters: dict = None):
        """Creates device.

        Keyword arguments:
        data -- device data
        parameters -- editable parameters
        """

        self.__dict__["_data"] = {}
        self.__dict__["_parameters"] = {}

        if data is not None:
            self.set_data(data)

        if parameters is not None:
            self.set_parameters(parameters)

        self.product = None
        self.uid = None
        self.password = None
        self.struct = []
        self.bucket = FrameBucket()
        self._queue = []
        self._is_on = False

    def __getattr__(self, name: str) -> None:
        """Gets current data item as class attribute.

        Keyword arguments:
        name -- name of property to get
        """
        key = name.upper()
        if key in self._data:
            return self._data[key]

        if key in self._parameters:
            return self._parameters[key]

        return None

    def __setattr__(self, name: str, value) -> None:
        """Sets class attribute or device parameter.

        Keyword arguments:
        name -- attribute name
        value -- attribute value
        """
        key = name.upper()
        if key in self._data:
            raise AttributeError()

        if key in self._parameters:
            self._parameters[key].set(value)
            self._queue.append(self._parameters[key].request)
        else:
            self.__dict__[name] = value

    def has_data(self) -> bool:
        """Checks if device instance has any data."""
        return bool(self._data)

    def set_data(self, data: dict) -> None:
        """Sets device data received in CurrentData frame.

        Keyword arguments:
        data - data parsed from CurrentData response frame
        """
        self.bucket.fill(data[DATA_FRAMES])
        for name, value in data.items():
            if name in CURRENT_DATA:
                self._data[name] = value

    def has_parameters(self) -> bool:
        """Check if device instance has parameters."""
        return bool(self._parameters)

    def set_parameters(self, parameters: dict) -> None:
        """Sets device settings received in parameters frame."""
        for name, parameter in parameters.items():
            if name in EDITABLE_PARAMS:
                self._parameters[name] = Parameter(
                    name=name,
                    value=parameter["value"],
                    min_=parameter["min"],
                    max_=parameter["max"],
                )

        self._parameters["BOILER_CONTROL"] = Parameter(
            name="BOILER_CONTROL", value=int(self.is_on), min_=0, max_=1
        )

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
    def queue(self):
        """Clears and returns changed parameters queue."""
        queue = self._queue
        self._queue = []
        return queue

    @property
    def data(self):
        """Returns device data."""
        return self._data

    @property
    def parameters(self):
        """Returns device parameters."""
        return self._parameters

    @property
    def changes(self) -> list[Parameter]:
        """Returns changed device parameters."""
        changes = self.queue
        changes.extend(self.bucket.queue)
        return changes

    def __str__(self) -> str:
        """Converts device instance to a string."""
        output = f"""
Product:        {self.product}
Software Ver.:  {self.software}
UID:            {self.uid}
Password:       {self.password}
"""

        if self.has_data():
            output += "\nCurrent data:\n"
            for k, v in self._data.items():
                output += f" -- {k}: {v}\n"

        if self.has_parameters():
            output += "\nEditable parameters:\n"
            for _, parameter in self._parameters.items():
                output += f" -- {parameter}\n"

        return output.lstrip()


class EcoMAX(Device):
    """ecoMAX device representation."""

    address = ECOMAX_ADDRESS


class EcoSTER(Device):
    """ecoSTER device representation."""

    address = ECOSTER_ADDRESS


class DeviceCollection:
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


class Parameter:
    """Device parameter representation."""

    def __init__(self, name: str, value, min_: int, max_: int):
        """Creates parameter."""
        self.name = name
        self.value = int(value)
        self.min_ = min_
        self.max_ = max_

    def set(self, value) -> None:
        """Sets parameter value.

        Keyword arguments:
        value -- new value to set parameter to
        """
        if self.value != value and self.min_ <= value <= self.max_:
            self.value = value

    @property
    def request(self) -> Request:
        """Returns request to change parameter."""
        if self.name == "BOILER_CONTROL":
            return BoilerControl(data=self.__dict__)

        return SetParameter(data=self.__dict__)

    def __repr__(self) -> str:
        """Returns serializable string representation."""
        return f"""Parameter(
    name = {self.name},
    value = {self.value},
    min_ = {self.min_},
    max_ = {self.max_}
)""".strip()

    def __str__(self) -> str:
        """Returns string representation."""
        return f"{self.name}: {self.value} (range {self.min_} - {self.max_})"

    def __int__(self) -> int:
        """Returns integer representation of parameter value.

        Keyword arguments:
        other -- other value to compare to
        """
        return int(self.value)

    def __eq__(self, other) -> int:
        """Compares if parameter value is equal to other.

        Keyword arguments:
        other -- other value to compare to
        """
        return self.value == other

    def __ge__(self, other) -> int:
        """Compares if parameter value is greater or equal to other.

        Keyword arguments:
        other -- other value to compare to
        """
        return self.value >= other

    def __gt__(self, other) -> int:
        """Compares if parameter value is greater than other.

        Keyword arguments:
        other -- other value to compare to
        """
        return self.value > other

    def __le__(self, other) -> int:
        """Compares if parameter value is less or equal to other.

        Keyword arguments:
        other -- other value to compare to
        """
        return self.value <= other

    def __lt__(self, other) -> int:
        """Compares if parameter value is less that other.

        Keyword arguments:
        other -- other value to compare to
        """
        return self.value < other
