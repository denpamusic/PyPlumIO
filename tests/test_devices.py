import pytest

from pyplumio.constants import MODULE_A
from pyplumio.devices import EcoMAX, Parameter

_test_data = {
    "modeString": "Heating",
    "boilerPowerKW": 16,
    "boilerPower": 30,
    "temperatures": {
        "tempCO": 60,
        "tempFlueGas": 60,
        "tempExternalSensor": 30,
        "tempCWU": 40,
        "tempFeeder": 51,
    },
    "tempCOSet": 60,
    "tempCWUSet": 51,
    "outputs": {
        "pumpCOWorks": True,
        "fanWorks": True,
        "pumpCWUWorks": True,
        "feederWorks": True,
        "lighterWorks": True,
    },
    "fanPower": 100,
    "fuelLevel": 70,
    "fuelStream": 1.27,
    "versions": {
        MODULE_A: "1.1.15",
    },
}

_test_parameters = {
    "AUTO_SUMMER": {
        "value": 1,
        "min": 0,
        "max": 1,
    }
}


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
    assert ecomax_with_data.data["MODE"] == "Heating"


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
    assert ecomax_with_data.changes[0].name == "AUTO_SUMMER"


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
    max_ = 1,
    changed = False
)""".strip()

    assert repr(parameter) == output


def test_parameter__str__(parameter: Parameter):
    assert str(parameter) == "AUTO_SUMMER: 1 (range 0 - 1)"
