import pytest

from pyplumio.constants import (
    DATA_FAN_POWER,
    DATA_FRAMES,
    DATA_FUEL_CONSUMPTION,
    DATA_FUEL_LEVEL,
    DATA_HEATING_TARGET,
    DATA_LOAD,
    DATA_MODE,
    DATA_POWER,
    DATA_WATER_HEATER_TARGET,
    MODULE_A,
)
from pyplumio.devices import ECOMAX_ADDRESS, DevicesCollection, EcoMAX
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
    DATA_HEATING_TARGET: 60,
    DATA_WATER_HEATER_TARGET: 51,
    DATA_FAN_POWER: 100,
    DATA_FUEL_LEVEL: 70,
    DATA_FUEL_CONSUMPTION: 1.27,
    MODULE_A: "1.1.15",
    "heating_temp": 60,
    "exhaust_temp": 60,
    "outside_temp": 30,
    "water_heater_temp": 40,
    "feeder_temp": 51,
    "heating_pump": True,
    "fan": True,
    "water_heater_pump": True,
    "feeder": True,
    "lighter": True,
}

_test_parameters = {"summer_mode": [1, 0, 1]}


@pytest.fixture
def ecomax() -> EcoMAX:
    return EcoMAX()


@pytest.fixture
def ecomax_with_data(ecomax) -> EcoMAX:
    ecomax.set_data(_test_data)
    ecomax.set_parameters(_test_parameters)
    return ecomax


@pytest.fixture
def devices() -> DevicesCollection:
    devices = DevicesCollection()
    devices.get(ECOMAX_ADDRESS)
    return devices


def test_set_data(ecomax_with_data: EcoMAX):
    ecomax_with_data.set_data(_test_data)
    assert ecomax_with_data.data["mode"] == 3


def test_get_attr_from_data(ecomax_with_data: EcoMAX):
    assert ecomax_with_data.mode == "Heating"


def test_has_mixers(ecomax):
    assert not ecomax.has_mixers()


def test_get_mode(ecomax: EcoMAX):
    data = _test_data
    data[DATA_MODE] = 69
    ecomax.set_data(data)
    assert ecomax.mode == "Unknown"


def test_get_parameters(ecomax_with_data: EcoMAX):
    assert ecomax_with_data.parameters["summer_mode"] == 1


def test_get_attr_from_parameters(ecomax_with_data: EcoMAX):
    assert ecomax_with_data.summer_mode == 1


def test_set_attr_from_parameters(ecomax_with_data: EcoMAX):
    ecomax_with_data.summer_mode = 0
    assert ecomax_with_data.summer_mode == 0


def test_set_attr_from_parameters_out_of_range(ecomax_with_data: EcoMAX):
    ecomax_with_data.summer_mode = 39
    assert ecomax_with_data.summer_mode == 1


def test_changed_parameters(ecomax_with_data: EcoMAX):
    ecomax_with_data.summer_mode = 0
    assert (
        ecomax_with_data.changes[0].message
        == requests.SetParameter(data={"name": "summer_mode", "value": 0}).message
    )


def test_software(ecomax_with_data: EcoMAX):
    assert ecomax_with_data.software == "1.1.15"


def test_software_unknown(ecomax: EcoMAX):
    assert ecomax.software is None


def test_is_on(ecomax_with_data: EcoMAX):
    assert ecomax_with_data.is_on


def test_is_on_unknown(ecomax: EcoMAX):
    assert not ecomax.is_on


def test_to_str(ecomax_with_data: EcoMAX):
    assert "Software Ver.:  1.1.15" in str(ecomax_with_data)


def test_get_attr_from_collection(devices: DevicesCollection):
    assert isinstance(devices.ecomax, EcoMAX)


def test_get_unknown_attr_from_collection(devices: DevicesCollection):
    assert devices.nonexistent is None


def test_collection_length(devices: DevicesCollection):
    assert len(devices) == 1


def test_collection_has_device(devices: DevicesCollection):
    assert devices.has(ECOMAX_ADDRESS)
    assert devices.has("ecomax")


def test_collection_has_no_device(devices: DevicesCollection):
    assert not devices.has(0x0)
    assert not devices.has("nonexistent")


def test_get_device_from_collection(devices: DevicesCollection):
    assert isinstance(devices.get(ECOMAX_ADDRESS), EcoMAX)


def test_init_device_from_collection():
    devices = DevicesCollection()
    assert isinstance(devices.get(ECOMAX_ADDRESS), EcoMAX)


def test_init_unknown_device_from_collection(devices: DevicesCollection):
    assert devices.get(0x0) is None
