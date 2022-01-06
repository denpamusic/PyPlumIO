from __future__ import annotations

from datetime import datetime

from . import util


class EcoMax:
    """ """

    software: str = None
    updated: str = None
    product: str = None
    uid: str = None
    password: str = None
    struct: list = []
    _parameters: dict = {}
    _data: dict = {}

    def has_data(self) -> bool:
        return self.updated is not None

    def set_data(self, data: dict) -> None:
        self._data['software'] = data['versions']['moduleASoftVer']
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

        self.updated = datetime.now()

    def set_parameters(self, parameters: dict) -> None:
        self._parameters = parameters

    def data(self, *args):
        data = []
        for arg in args:
            if self._data[arg] is not None:
                data.append(self._data[arg])

        return data

    def __str__(self) -> str:
        co_temp = util.celsius(self._data['co_temp'])
        co_target = util.celsius(self._data['co_target'])
        cwu_temp = util.celsius(self._data['cwu_temp'])
        cwu_target = util.celsius(self._data['cwu_target'])

        return f"""
Product:    {self.product}
Version:    {self.software}
UID:        {self.uid}
Password:   {self.password}
Mode:       {self._data['mode']}
Power:      {util.kw(self._data['power'])}
Fan:        {util.is_working(self._data['fan'])}
Fan Power:  {util.percent(self._data['fan_power'])}
CO Temp:    {co_temp} / {co_target}
CO Pump:    {util.is_working(self._data['co_pump'])}
CWU Temp:   {cwu_temp} / {cwu_target}
CWU Pump:   {util.is_working(self._data['cwu_pump'])}
Exhaust:    {util.celsius(self._data['exhaust_temp'])}
Outdoor:    {util.celsius(self._data['outdoor_temp'])}
Feeder:     {util.celsius(self._data['feeder_temp'])}
Fuel Level: {util.percent(self._data['fuel_level'])}
Fuel Flow:  {util.kgh(self._data['fuel_flow'])}
Updated:    {self.updated.strftime('%d.%m.%Y %H:%M:%S')}
Drawn:      {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
""".strip()
