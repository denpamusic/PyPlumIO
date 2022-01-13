"""Contains classes for supported devices."""
from __future__ import annotations

from .constants import EDITABLE_PARAMS, MODULE_A


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
    _parameters_changed: bool = False
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

        return None

    def __setattr__(self, name: str, value) -> None:
        """Sets class attribute or device parameter.

        Keyword arguments:
        name -- attribute name
        value -- attribute value
        """
        key = name.upper()
        if key in self._parameters and self._parameters[key].value != value:
            self._parameters_changed = True
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
        self._data["MODE"] = data["modeString"]
        self._data["POWER"] = data["boilerPowerKW"]
        self._data["POWER_PCT"] = data["boilerPower"]
        self._data["CO_TARGET"] = data["tempCOSet"]
        self._data["CO_TEMP"] = data["temperatures"]["tempCO"]
        self._data["CO_PUMP"] = data["outputs"]["pumpCOWorks"]
        self._data["EXHAUST_TEMP"] = data["temperatures"]["tempFlueGas"]
        self._data["OUTSIDE_TEMP"] = data["temperatures"]["tempExternalSensor"]
        self._data["FAN"] = data["outputs"]["fanWorks"]
        self._data["FAN_POWER"] = data["fanPower"]
        self._data["CWU_TARGET"] = data["tempCWUSet"]
        self._data["CWU_TEMP"] = data["temperatures"]["tempCWU"]
        self._data["CWU_PUMP"] = data["outputs"]["pumpCWUWorks"]
        self._data["FEEDER"] = data["outputs"]["feederWorks"]
        self._data["FEEDER_TEMP"] = data["temperatures"]["tempFeeder"]
        self._data["FUEL_LEVEL"] = data["fuelLevel"]
        self._data["FUEL_FLOW"] = data["fuelStream"]
        self._data["LIGHTER"] = data["outputs"]["lighterWorks"]
        self.software = data["versions"][MODULE_A]

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
        changed = []
        if self._parameters_changed:
            for _, param in self._parameters.items():
                if param.changed:
                    changed.append(param)

        return changed

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

    def __init__(
        self, name: str, value: int, min_: int, max_: int, changed: bool = False
    ):
        self.name = name
        self.value = value
        self.min_ = min_
        self.max_ = max_
        self.changed = changed

    def set(self, value) -> None:
        """Sets parameter value.

        Keyword arguments:
        value -- new value to set parameter to
        """
        if self.min_ <= value <= self.max_:
            self.value = value

        self.changed = True

    def __repr__(self) -> str:
        """Returns serializable string representation."""
        return f"""Parameter(
    name = {self.name},
    value = {self.value},
    min_ = {self.min_},
    max_ = {self.max_},
    changed = {self.changed}
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
