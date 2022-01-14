"""Contains classes for supported devices."""
from __future__ import annotations

from .constants import CURRENT_DATA, DATA_MODE, EDITABLE_PARAMS, MODES, MODULE_A
from .frame import Request
from .frames.requests import BoilerControl, SetParameter


class EcoMAX:
    """EcoMAX device representation.

    Passed to the user-defined callback method.
    """

    software: str = None
    product: str = None
    uid: str = None
    password: str = None
    struct: list = []
    _parameters: dict = {}
    _data: dict = {}

    def __init__(self, data: dict = None, parameters: dict = None):
        """Create ecoMAX device representation."""

        if data is not None:
            self.set_data(data)

        if parameters is not None:
            self.set_parameters(parameters)

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

        return self.__dict__[name]

    def __setattr__(self, name: str, value) -> None:
        """Sets class attribute or device parameter.

        Keyword arguments:
        name -- attribute name
        value -- attribute value
        """
        key = name.upper()
        if key in self._data:
            raise NotImplementedError()

        if key in self._parameters:
            self._parameters[key].set(value)
        else:
            self.__dict__[name] = value

    def has_data(self) -> bool:
        """Checks if EcoMAX instance has any data."""
        return bool(self._data)

    def set_data(self, data: dict) -> None:
        """Sets EcoMAX data received in CurrentData frame.

        Keyword arguments:
        data - data parsed from CurrentData response frame
        """
        for name, value in data.items():
            if name in CURRENT_DATA:
                self._data[name] = value

        self.software = data[MODULE_A]
        self.set_parameters(
            {"BOILER_CONTROL": {"value": int(self.is_on), "min": 0, "max": 1}}
        )

    def has_parameters(self) -> bool:
        """Check if ecoMAX instance has parameters."""
        return bool(self._parameters)

    def set_parameters(self, parameters: dict) -> None:
        """Sets EcoMAX settings received in Parameters frame."""
        for name, parameter in parameters.items():
            if name in EDITABLE_PARAMS:
                self._parameters[name] = Parameter(
                    name=name,
                    value=parameter["value"],
                    min_=parameter["min"],
                    max_=parameter["max"],
                )

    @property
    def is_on(self) -> bool:
        """Returns current state."""
        if self._data:
            return bool(self._data[DATA_MODE] != 0)

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
    def data(self):
        """Returns EcoMAX data."""
        return self._data

    @property
    def parameters(self):
        """Returns EcoMAX parameters."""
        return self._parameters

    @property
    def changes(self) -> list[Parameter]:
        """Returns changed device parameters."""
        return [
            v.queue() for _, v in self._parameters.items() if v.changed and not v.queued
        ]

    def __str__(self) -> str:
        """Converts EcoMAX instance to a string."""
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
            output += "\nRegulator parameters:\n"
            for _, parameter in self._parameters.items():
                output += f" -- {parameter}\n"

        return output.lstrip()


class Parameter:
    """Device parameter representation."""

    _changed = False
    _queued = False

    def __init__(self, name: str, value, min_: int, max_: int):
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
            self._changed = True

    def queue(self) -> Parameter:
        """Marks parameter as queued to write."""
        self._queued = True
        return self

    @property
    def request(self) -> Request:
        """Returns request to change parameter."""
        if self.name == "BOILER_CONTROL":
            return BoilerControl(data=self.__dict__)

        return SetParameter(data=self.__dict__)

    @property
    def queued(self) -> bool:
        """Returns queued property."""
        return self._queued

    @property
    def changed(self) -> bool:
        """Returns changed property."""
        return self._changed

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
