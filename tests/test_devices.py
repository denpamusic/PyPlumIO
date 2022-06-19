"""Test PyPlumIO devices."""

import math
from unittest.mock import patch

import pytest

from pyplumio.constants import (
    DATA_FAN_POWER,
    DATA_FUEL_CONSUMPTION,
    DATA_FUEL_LEVEL,
    DATA_LOAD,
    DATA_MODE,
    DATA_MODULES,
    DATA_PASSWORD,
    DATA_POWER,
    DATA_PRODUCT,
    DATA_UNKNOWN,
    ECOMAX_ADDRESS,
)
from pyplumio.devices import MODE_HEATING, MODES, DeviceCollection, EcoMAX, EcoSTER
from pyplumio.exceptions import UninitializedParameterError
from pyplumio.frames import messages, requests, responses
from pyplumio.frames.messages import RegData
from pyplumio.frames.responses import DataSchema
from pyplumio.helpers.parameter import Parameter
from pyplumio.helpers.product_info import ConnectedModules, ProductInfo
from pyplumio.structures.device_parameters import PARAMETER_BOILER_CONTROL
from pyplumio.structures.frame_versions import FRAME_VERSIONS
from pyplumio.structures.statuses import HEATING_TARGET, WATER_HEATER_TARGET

from .frames.test_messages import _regdata_bytes

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
    DATA_PASSWORD: "0000",
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
    _test_data[DATA_PRODUCT] = ProductInfo(model="test_model")
    ecomax.set_data(_test_data)
    ecomax.set_parameters(_test_parameters)
    return ecomax


@pytest.fixture(name="ecomax_with_version")
def fixture_ecomax_with_version(ecomax_with_data: EcoMAX) -> EcoMAX:
    """Return ecoMAX instance with module version data."""
    connected_modules = ConnectedModules(module_a="1.1.15")
    ecomax_with_data.set_data({DATA_MODULES: connected_modules})
    return ecomax_with_data


def test_set_data(ecomax: EcoMAX) -> None:
    """Test getting data from the ecoMAX."""
    ecomax.set_data(_test_data)
    assert ecomax.data["mode"] == MODE_HEATING


def test_get_attr_from_data(ecomax_with_data: EcoMAX) -> None:
    """Test getting data from object attribute."""
    assert ecomax_with_data.mode == MODES[MODE_HEATING]


def test_has_attr_from_data(ecomax_with_data: EcoMAX) -> None:
    """Test that hasattr works."""
    assert not hasattr(ecomax_with_data, "nonexistent")
    assert hasattr(ecomax_with_data, "heating_temp")


def test_get_boiler_control_param(ecomax_with_data: EcoMAX) -> None:
    """Test getting boiler control parameter from the ecoMAX."""
    ecomax_with_data.set_data(_test_data)
    assert isinstance(ecomax_with_data.parameters[PARAMETER_BOILER_CONTROL], Parameter)


def test_set_data_from_regdata(ecomax: EcoMAX, data_schema: DataSchema) -> None:
    """Test setting data from regdata."""
    regdata = RegData(message=_regdata_bytes)
    ecomax.set_data(data_schema.data)
    ecomax.set_data(regdata.data)
    assert ecomax.data[DATA_MODE] == 0
    assert round(ecomax.data["heating_temp"], 2) == 22.38
    assert ecomax.data["heating_target"] == 41
    assert not ecomax.data["heating_pump"]
    assert math.isnan(ecomax.data["outside_temp"])
    assert ecomax.data["183"] == "0.0.0.0"
    assert ecomax.data["184"] == "255.255.255.0"
    assert ecomax.data["195"] == ""


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


def test_product(ecomax_with_data: EcoMAX) -> None:
    """Test product property."""
    assert ecomax_with_data.product.model == "test_model"


def test_product_not_available(ecomax: EcoMAX) -> None:
    """Test product property when data is not available."""
    assert ecomax.product.model is None


def test_modules(ecomax_with_version: EcoMAX) -> None:
    """Test modules property."""
    assert ecomax_with_version.modules.module_a == "1.1.15"


def test_modules_not_available(ecomax: EcoMAX) -> None:
    """Test modules property when data is not available."""
    assert ecomax.modules.module_a is None


def test_password(ecomax_with_data: EcoMAX) -> None:
    """Test service password property."""
    assert ecomax_with_data.password == "0000"


def test_password_not_available(ecomax: EcoMAX) -> None:
    """Test service password property when data is not available."""
    assert ecomax.password is None


def test_required_requests(ecomax: EcoMAX, ecoster: EcoSTER) -> None:
    """Test that required requests property is correctly set."""
    assert ecomax.required_requests == (
        requests.UID,
        requests.Password,
        requests.BoilerParameters,
        requests.MixerParameters,
    )
    assert not ecoster.required_requests


def test_data_and_parameters_responses(ecomax: EcoMAX, ecoster: EcoSTER) -> None:
    """Test that data responses property is correctly set."""
    assert ecomax.data_responses == (
        responses.UID,
        responses.DataSchema,
        responses.Password,
        messages.CurrentData,
        messages.RegData,
    )
    assert ecomax.parameter_responses == responses.BoilerParameters
    assert not ecoster.data_responses
    assert not ecoster.parameter_responses


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
    print(str(ecomax_with_version))
    assert "Mixers:" in str(ecomax_with_version)


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


def test_get_attr_from_collection(devices: DeviceCollection) -> None:
    """Test get instance from devices collection."""
    assert isinstance(devices.ecomax, EcoMAX)


def test_get_unknown_attr_from_collection(devices: DeviceCollection) -> None:
    """Test checking for nonexistent key in devices collection."""
    assert not hasattr(devices, "nonexistent")


def test_collection_length(devices: DeviceCollection) -> None:
    """Test len method on devices collection."""
    assert len(devices) == 1


def test_collection_has_device(devices: DeviceCollection) -> None:
    """Test if collection has device with address or name."""
    assert devices.has(ECOMAX_ADDRESS)
    assert devices.has("ecomax")


def test_collection_has_no_device(devices: DeviceCollection) -> None:
    """Test that collection doesn't have device with address or name."""
    assert not devices.has(0x0)
    assert not devices.has("nonexistent")


def test_get_device_from_collection(devices: DeviceCollection) -> None:
    """Test getting device from the collection with address."""
    assert isinstance(devices.get(ECOMAX_ADDRESS), EcoMAX)


def test_init_device_from_collection() -> None:
    """Test initialization of device in the collection."""
    devices = DeviceCollection()
    assert isinstance(devices.get(ECOMAX_ADDRESS), EcoMAX)


def test_init_unknown_device_from_collection(devices: DeviceCollection) -> None:
    """Test initialization of unknown device in the collection."""
    assert devices.get(0x0) is None
