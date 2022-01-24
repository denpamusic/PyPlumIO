import pytest

from pyplumio.constants import (
    DATA_CO_TARGET,
    DATA_CWU_TARGET,
    DATA_FAN_POWER,
    DATA_FRAMES,
    DATA_FUEL_CONSUMPTION,
    DATA_FUEL_LEVEL,
    DATA_LOAD,
    DATA_MODE,
    DATA_POWER,
    MODULE_PANEL,
)
from pyplumio.devices import EcoMAX, Parameter
from pyplumio.frames import requests

_test_data = {
    DATA_FRAMES: {
        49: 364,
        50: 364,
        54: 1,
        56: 90,
        57: 1,
        61: 28217,
        80: 1,
        81: 1,
        82: 1,
        83: 1,
    },
    DATA_MODE: 3,
    DATA_POWER: 16,
    DATA_LOAD: 30,
    DATA_CO_TARGET: 60,
    DATA_CWU_TARGET: 51,
    DATA_FAN_POWER: 100,
    DATA_FUEL_LEVEL: 70,
    DATA_FUEL_CONSUMPTION: 1.27,
    MODULE_PANEL: "1.1.15",
    "CO_TEMP": 60,
    "EXHAUST_TEMP": 60,
    "OUTSIDE_TEMP": 30,
    "CWU_TEMP": 40,
    "FEEDER_TEMP": 51,
    "CO_PUMP": True,
    "FAN": True,
    "CWU_PUMP": True,
    "FEEDER": True,
    "LIGHTER": True,
}

_test_parameters = {"AUTO_SUMMER": [1, 0, 1]}


@pytest.fixture
def ecomax() -> EcoMAX:
    return EcoMAX()


@pytest.fixture
def ecomax_with_data(ecomax) -> EcoMAX:
    ecomax.set_data(_test_data)
    ecomax.set_parameters(_test_parameters)
    return ecomax


@pytest.fixture
def parameter() -> Parameter:
    return Parameter(name="AUTO_SUMMER", value=1, min_=0, max_=1)


def test_has_no_data(ecomax: EcoMAX):
    assert not ecomax.has_data()


def test_has_no_parameters(ecomax: EcoMAX):
    assert not ecomax.has_parameters()


def test_has_data(ecomax_with_data: EcoMAX):
    assert ecomax_with_data.has_data()


def test_set_data(ecomax_with_data: EcoMAX):
    ecomax_with_data.set_data(_test_data)
    assert ecomax_with_data.data["MODE"] == 3


def test_get_attr_from_data(ecomax_with_data: EcoMAX):
    assert ecomax_with_data.mode == "Heating"


def test_get_parameters(ecomax_with_data: EcoMAX):
    assert ecomax_with_data.parameters["AUTO_SUMMER"] == 1


def test_get_attr_from_parameters(ecomax_with_data: EcoMAX):
    assert ecomax_with_data.auto_summer == 1


def test_set_attr_from_parameters(ecomax_with_data: EcoMAX):
    ecomax_with_data.auto_summer = 0
    assert ecomax_with_data.auto_summer == 0


def test_set_attr_from_parameters_out_of_range(ecomax_with_data: EcoMAX):
    ecomax_with_data.auto_summer = 39
    assert ecomax_with_data.auto_summer == 1


def test_changed_parameters(ecomax_with_data: EcoMAX):
    ecomax_with_data.auto_summer = 0
    assert (
        ecomax_with_data.changes[0].message
        == requests.SetParameter(data={"name": "AUTO_SUMMER", "value": 0}).message
    )


def test_has_parameters(ecomax_with_data: EcoMAX):
    assert ecomax_with_data.has_parameters()


def test_to_str(ecomax_with_data: EcoMAX):
    assert "Software Ver.:  1.1.15" in str(ecomax_with_data)


def test_parameter_set(parameter: Parameter):
    parameter.set(0)
    assert parameter == 0


def test_parameter_set_out_of_range(parameter: Parameter):
    parameter.set(39)
    assert parameter == 1


def test_parameter_compare(parameter: Parameter):
    assert parameter == 1
    assert parameter < 2
    assert parameter > 0
    assert 0 <= parameter <= 1


def test_parameter__repr__(parameter: Parameter):
    output = """Parameter(
    name = AUTO_SUMMER,
    value = 1,
    min_ = 0,
    max_ = 1
)""".strip()

    assert repr(parameter) == output


def test_parameter__str__(parameter: Parameter):
    assert str(parameter) == "AUTO_SUMMER: 1 (range 0 - 1)"
