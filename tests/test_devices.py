"""Test PyPlumIO devices."""

from unittest.mock import patch

import pytest

from pyplumio.constants import (
    DATA_FAN_POWER,
    DATA_FUEL_CONSUMPTION,
    DATA_FUEL_LEVEL,
    DATA_LOAD,
    DATA_MODE,
    DATA_POWER,
    DATA_UNKNOWN,
    ECOMAX_ADDRESS,
)
from pyplumio.devices import MODE_HEATING, MODES, DevicesCollection, EcoMAX
from pyplumio.exceptions import UninitializedParameterError
from pyplumio.frames import requests
from pyplumio.helpers.parameter import Parameter
from pyplumio.structures.device_parameters import PARAMETER_BOILER_CONTROL
from pyplumio.structures.frame_versions import FRAME_VERSIONS
from pyplumio.structures.modules import (
    MODULE_A,
    MODULE_B,
    MODULE_C,
    MODULE_ECOSTER,
    MODULE_LAMBDA,
    MODULE_PANEL,
)
from pyplumio.structures.statuses import HEATING_TARGET, WATER_HEATER_TARGET

_test_data = {
    FRAME_VERSIONS: {
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
    DATA_MODE: MODE_HEATING,
    DATA_POWER: 16,
    DATA_LOAD: 30,
    HEATING_TARGET: 60,
    WATER_HEATER_TARGET: 51,
    DATA_FAN_POWER: 100,
    DATA_FUEL_LEVEL: 70,
    DATA_FUEL_CONSUMPTION: 1.27,
    MODULE_A: None,
    MODULE_B: None,
    MODULE_C: None,
    MODULE_LAMBDA: None,
    MODULE_ECOSTER: None,
    MODULE_PANEL: None,
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


@pytest.fixture(name="ecomax_with_data")
def fixture_ecomax_with_data(ecomax: EcoMAX) -> EcoMAX:
    """Return ecoMAX instance with test data."""
    ecomax.set_data(_test_data)
    ecomax.set_parameters(_test_parameters)
    return ecomax


@pytest.fixture(name="ecomax_with_version")
def fixture_ecomax_with_version(ecomax_with_data: EcoMAX) -> EcoMAX:
    """Return ecoMAX instance with version data."""
    ecomax_with_data.set_data({MODULE_A: "1.1.15"})
    return ecomax_with_data


def test_set_data(ecomax: EcoMAX) -> None:
    """Test getting data from the ecoMAX."""
    ecomax.set_data(_test_data)
    assert ecomax.data["mode"] == MODE_HEATING


def test_get_attr_from_data(ecomax_with_data: EcoMAX) -> None:
    """Test getting data from object attribute."""
    assert ecomax_with_data.mode == MODES[MODE_HEATING]


def test_get_boiler_control_param(ecomax_with_data: EcoMAX) -> None:
    """Test getting boiler control parameter from the ecoMAX."""
    ecomax_with_data.set_data(_test_data)
    assert isinstance(ecomax_with_data.parameters[PARAMETER_BOILER_CONTROL], Parameter)


def test_get_mode(ecomax: EcoMAX) -> None:
    """Test getting mode."""
    data = _test_data
    ecomax.set_data(data)
    assert ecomax.mode == MODES[MODE_HEATING]

    # Test with unknown mode.
    data[DATA_MODE] = 69
    ecomax.set_data(data)
    assert ecomax.mode == DATA_UNKNOWN


def test_get_mode_unavailable(ecomax: EcoMAX) -> None:
    """Test mode unavailable."""
    assert ecomax.mode is None


def test_get_parameters(ecomax_with_data: EcoMAX) -> None:
    """Test getting value from the parameters."""
    assert ecomax_with_data.parameters["summer_mode"] == 1


def test_get_attr_from_parameters(ecomax_with_data: EcoMAX) -> None:
    """Test getting value from the attributes."""
    assert ecomax_with_data.summer_mode == 1


def test_get_attr_from_nonexistent(ecomax_with_data: EcoMAX) -> None:
    """Test checking for nonexistent attribute."""
    assert not hasattr(ecomax_with_data, "nonexistent")


def test_set_attr_from_parameters(ecomax_with_data: EcoMAX) -> None:
    """Test setting parameter via object attributes."""
    ecomax_with_data.summer_mode = 0
    assert ecomax_with_data.summer_mode == 0


def test_set_attr_from_parameters_out_of_range(ecomax_with_data: EcoMAX) -> None:
    """Test setting parameter out of range."""
    ecomax_with_data.summer_mode = 39
    assert ecomax_with_data.summer_mode == 1


def test_set_attr_from_data(ecomax_with_data: EcoMAX):
    """Test setting immutable data."""
    with pytest.raises(AttributeError):
        ecomax_with_data.heating_temp = 0


def test_set_attr_from_parameters_uninitialized(ecomax_with_data: EcoMAX) -> None:
    """Test trying to set uninitialized parameter."""
    with pytest.raises(UninitializedParameterError):
        ecomax_with_data.circulation_control = True


def test_changed_parameters(ecomax_with_data: EcoMAX) -> None:
    """Test getting changed parameters."""
    ecomax_with_data.summer_mode = 0
    assert (
        ecomax_with_data.changes[0].message
        == requests.SetBoilerParameter(data={"name": "summer_mode", "value": 0}).message
    )


def test_software(ecomax_with_version: EcoMAX) -> None:
    """Test software version property."""
    assert ecomax_with_version.software == "1.1.15"


def test_software_not_available(ecomax: EcoMAX) -> None:
    """Test software version property when data is not yet available."""
    assert ecomax.software is None


def test_software_is_unknown(ecomax_with_data: EcoMAX) -> None:
    """Test software property when version data is missing."""
    assert ecomax_with_data.software == "Unknown"


def test_fuel_burned(ecomax: EcoMAX) -> None:
    """Test burned fuel property calculations and reset."""
    # Mock time to return 10 seconds on init and 20 seconds on
    # set data call, resulting in predictable 10 seconds time delta.
    with patch("time.time") as mock_time:
        mock_time.return_value = 10
        ecomax = EcoMAX()
        mock_time.return_value = 20
        ecomax.set_data({DATA_FUEL_CONSUMPTION: 3.6})

    assert ecomax.fuel_burned == 0.01
    # Test that fuel_burned is reset on the second call.
    assert ecomax.fuel_burned == 0

    # Test that time function was called exactly two times.
    # Firstly on init and secondly on set_data call.
    assert len(mock_time.mock_calls) == 2


def test_is_on(ecomax_with_data: EcoMAX) -> None:
    """Test ecoMAX state."""
    assert ecomax_with_data.is_on


def test_is_on_unknown(ecomax: EcoMAX) -> None:
    """Test ecoMAX state when state is unknown."""
    assert not ecomax.is_on


def test_str(ecomax_with_version: EcoMAX) -> None:
    """Test ecoMAX string representation."""
    assert "Software Ver.:  1.1.15" in str(ecomax_with_version)


def test_repr(ecomax: EcoMAX) -> None:
    """Test ecoMAX serializable representation."""
    assert """EcoMAX(
    data = {},
    parameters = {}
)
""".strip() == repr(
        ecomax
    )


def test_has(ecomax_with_data: EcoMAX) -> None:
    """Test checking for key with has function."""
    assert ecomax_with_data.has("summer_mode")


def test_get_attr_from_collection(devices: DevicesCollection) -> None:
    """Test get instance from devices collection."""
    assert isinstance(devices.ecomax, EcoMAX)


def test_get_unknown_attr_from_collection(devices: DevicesCollection) -> None:
    """Test checking for nonexistent key in devices collection."""
    assert not hasattr(devices, "nonexistent")


def test_collection_length(devices: DevicesCollection) -> None:
    """Test len method on devices collection."""
    assert len(devices) == 1


def test_collection_has_device(devices: DevicesCollection) -> None:
    """Test if collection has device with address or name."""
    assert devices.has(ECOMAX_ADDRESS)
    assert devices.has("ecomax")


def test_collection_has_no_device(devices: DevicesCollection) -> None:
    """Test that collection doesn't have device with address or name."""
    assert not devices.has(0x0)
    assert not devices.has("nonexistent")


def test_get_device_from_collection(devices: DevicesCollection) -> None:
    """Test getting device from the collection with address."""
    assert isinstance(devices.get(ECOMAX_ADDRESS), EcoMAX)


def test_init_device_from_collection() -> None:
    """Test initialization of device in the collection."""
    devices = DevicesCollection()
    assert isinstance(devices.get(ECOMAX_ADDRESS), EcoMAX)


def test_init_unknown_device_from_collection(devices: DevicesCollection) -> None:
    """Test initialization of unknown device in the collection."""
    assert devices.get(0x0) is None
