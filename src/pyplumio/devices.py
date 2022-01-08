"""Contains classes for supported devices."""
from __future__ import annotations

from datetime import datetime


class EcoMAX:
    """Class for storing ecoMAX device state.

    Passed to callback method when receiving frame.
    """

    software: str = None
    updated: str = None
    product: str = None
    uid: str = None
    password: str = None
    struct: list = []
    _parameters: dict = {}
    _data: dict = {}

    def __getattr__(self, item: str):
        """Gets current data item as class attribute.

        Keyword arguments:
        item -- name of property to get
        """
        item = item.upper()
        if item in self._data:
            return item

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

        self.software = data["versions"]["moduleASoftVer"]
        self.updated = datetime.now()

    def has_parameters(self) -> bool:
        """Check if ecoMAX instance has parameters."""
        return bool(self._parameters)

    def set_parameters(self, parameters: dict) -> None:
        """Sets EcoMAX settings received in Parameters frame."""
        self._parameters = parameters

    def data(self):
        """Returns EcoMAX data as a tuple. Accepts list of keys."""
        return self._data

    def __str__(self) -> str:
        """Converts EcoMAX instance to a string."""
        output = f"""
Product:        {self.product}
Software Ver.:  {self.software}
UID:            {self.uid}
Password:       {self.password}
Updated:        {self.updated.strftime('%d.%m.%Y %H:%M:%S')}
"""

        if self.has_data():
            output += "\nCurrent data:\n"
            for k, v in self._data.items():
                output += f" -- {k}: {v}\n"

        if self.has_parameters():
            output += "\n Regulator parameters:\n"
            for k, v in self._parameters.items():
                parameter_str = f"{v['value']} (range {v['min']} - {v['max']})"
                output += f" -- {k}: {parameter_str}\n"

        return output.lstrip()
