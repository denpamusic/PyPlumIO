"""Contains classes for supported devices."""
from __future__ import annotations

from datetime import datetime


class EcoMAX:
    """ Class for storing ecoMAX device state.

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

    def has_data(self) -> bool:
        """Checks if EcoMAX instance has any data."""
        return bool(self._data)

    def set_data(self, data: dict) -> None:
        """Sets EcoMAX data received in CurrentData frame.

        Keyword arguments:
        data - data parsed from CurrentData response frame
        """
        self._data['mode'] = data['modeString']
        self._data['power'] = data['boilerPowerKW']
        self._data['co_target'] = data['tempCOSet']
        self._data['co_temp'] = data['temperatures']['tempCO']
        self._data['co_pump'] = data['outputs']['pumpCOWorks']
        self._data['exhaust_temp'] = data['temperatures']['tempFlueGas']
        self._data['outdoor_temp'] = data['temperatures']['tempExternalSensor']
        self._data['fan'] = data['outputs']['fanWorks']
        self._data['fan_power'] = data['fanPower']
        self._data['cwu_target'] = data['tempCWUSet']
        self._data['cwu_temp'] = data['temperatures']['tempCWU']
        self._data['cwu_pump'] = data['outputs']['pumpCWUWorks']
        self._data['feeder_temp'] = data['temperatures']['tempFeeder']
        self._data['fuel_level'] = data['fuelLevel']
        self._data['fuel_flow'] = data['fuelStream']

        self.software = data['versions']['moduleASoftVer']
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
Product:   {self.product}
Version:   {self.software}
UID:       {self.uid}
Password:  {self.password}
Updated:   {self.updated.strftime('%d.%m.%Y %H:%M:%S')}
Drawn:     {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
"""

        if self.has_data():
            output += '\nCurrent Data:\n'
            for k, v in self._data.items():
                output += f' -- {k}: {v}\n'

        if self.has_parameters():
            output += '\nCurrent Parameters:\n'
            for k, v in self._parameters.items():
                parameter_str = f"{v['value']} (range: {v['min']}:{v['max']})"
                output += f' -- {k}: {parameter_str}\n'

        return output.lstrip()
