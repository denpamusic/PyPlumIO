"""Contains tests for parameter."""


from unittest.mock import patch

import pytest

from pyplumio.const import ATTR_EXTRA, ATTR_INDEX, ATTR_VALUE
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.frames.requests import (
    EcomaxControlRequest,
    SetEcomaxParameterRequest,
    SetMixerParameterRequest,
    SetThermostatParameterRequest,
)
from pyplumio.helpers.parameter import (
    STATE_OFF,
    STATE_ON,
    EcomaxBinaryParameter,
    EcomaxParameter,
    MixerParameter,
    ScheduleParameter,
    ThermostatParameter,
)
from pyplumio.helpers.typing import ParameterDataType
from pyplumio.structures.ecomax_parameters import ATTR_ECOMAX_CONTROL
from pyplumio.structures.thermostat_parameters import ATTR_THERMOSTAT_PROFILE


@pytest.fixture(name="parameter")
def fixture_parameter(ecomax: EcoMAX) -> EcomaxBinaryParameter:
    """Return instance of summer_mode parameter."""
    parameter = EcomaxBinaryParameter(
        device=ecomax,
        name="summer_mode",
        value=1,
        min_value=0,
        max_value=1,
    )
    ecomax.data["summer_mode"] = parameter
    return parameter


@patch("pyplumio.devices.ecomax.EcoMAX.subscribe_once")
async def test_parameter_set(
    mock_subscribe_once, parameter: EcomaxBinaryParameter, bypass_asyncio_sleep
) -> None:
    """Test setting parameter."""
    await parameter.set(0)
    assert parameter == STATE_OFF
    mock_subscribe_once.assert_called_once()
    callback = mock_subscribe_once.call_args.args[1]
    assert parameter.change_pending
    await callback(parameter)
    assert not parameter.change_pending
    with patch("pyplumio.helpers.parameter.Parameter.change_pending", False):
        assert await parameter.set(STATE_ON)

    assert parameter == 1


async def test_parameter_set_out_of_range(parameter: EcomaxBinaryParameter) -> None:
    """Test setting parameter with value out of allowed range."""
    with pytest.raises(ValueError):
        await parameter.set(39)


def test_parameter_relational(parameter: EcomaxBinaryParameter):
    """Test parameter subtraction."""
    assert (parameter - 1) == 0
    assert (parameter + 1) == 2
    assert (parameter * 5) == 5
    assert (parameter / 1) == 1
    assert (parameter // 1) == 1


def test_parameter_compare(parameter: EcomaxBinaryParameter) -> None:
    """Test parameter comparison."""
    assert parameter == 1
    parameter_tuple: ParameterDataType = (1, 0, 1)
    assert parameter == parameter_tuple
    assert not parameter != parameter_tuple
    assert parameter < 2
    assert parameter > 0
    assert 0 <= parameter <= 1


def test_parameter_int(parameter: EcomaxBinaryParameter) -> None:
    """Test conversion to integer."""
    assert int(parameter) == 1


def test_parameter_repr(parameter: EcomaxBinaryParameter) -> None:
    """Test parameter serilizable representation."""
    assert repr(parameter) == (
        "EcomaxBinaryParameter(device=EcoMAX, name=summer_mode, value=1, "
        + "min_value=0, max_value=1, extra=None)"
    )


def test_parameter_request(parameter: EcomaxBinaryParameter) -> None:
    """Test parameter set request instance."""
    assert isinstance(parameter.request, SetEcomaxParameterRequest)


def test_parameter_request_mixer(ecomax: EcoMAX) -> None:
    """Test set mixer parameter request instance."""
    parameter = MixerParameter(
        device=ecomax,
        name="mixer_target_temp",
        value=50,
        min_value=50,
        max_value=80,
        extra=0,
    )
    assert isinstance(parameter.request, SetMixerParameterRequest)


async def test_parameter_request_thermostat(
    ecomax: EcoMAX, bypass_asyncio_sleep
) -> None:
    """Test set thermostat parameter request instance."""
    parameter = ThermostatParameter(
        device=ecomax,
        name="party_target_temp",
        value=220,
        min_value=100,
        max_value=350,
        extra=12,
    )
    assert isinstance(parameter.request, SetThermostatParameterRequest)
    assert parameter.value == 22.0
    assert parameter.min_value == 10.0
    assert parameter.max_value == 35.0
    assert parameter.extra == 12
    await parameter.set(20)
    assert parameter.request.data == {ATTR_INDEX: 2, ATTR_VALUE: 200, ATTR_EXTRA: 12}
    assert parameter.request.message.hex() == "0ec8"


@patch("asyncio.Queue.put")
@patch("pyplumio.helpers.parameter._collect_schedule_data")
@patch("pyplumio.helpers.parameter.factory")
def test_parameter_request_schedule(
    mock_factory, mock_collect_schedule_data, mock_put, ecomax: EcoMAX
) -> None:
    """Terst request schedule."""
    parameter = ScheduleParameter(
        device=ecomax,
        name="schedule_test_parameter",
        value=5,
        min_value=0,
        max_value=30,
        extra="test",
    )
    request = parameter.request
    mock_collect_schedule_data.assert_called_once_with("test", ecomax)
    mock_factory.assert_called_once_with(
        "frames.requests.SetScheduleRequest",
        recipient=ecomax.address,
        data=mock_collect_schedule_data.return_value,
    )
    assert request == mock_factory.return_value


def test_parameter_request_control(ecomax: EcoMAX) -> None:
    """Test ecoMAX control parameter request instance."""
    parameter = EcomaxParameter(
        device=ecomax,
        name=ATTR_ECOMAX_CONTROL,
        value=1,
        min_value=0,
        max_value=1,
    )
    assert isinstance(parameter.request, EcomaxControlRequest)


def test_parameter_request_thermostat_profile(ecomax: EcoMAX) -> None:
    """Test thermostat profile parameter request instance."""
    parameter = EcomaxParameter(
        device=ecomax,
        name=ATTR_THERMOSTAT_PROFILE,
        value=0,
        min_value=0,
        max_value=5,
    )
    assert isinstance(parameter.request, SetThermostatParameterRequest)


@patch("asyncio.Queue.put")
async def test_parameter_request_with_unchanged_value(
    mock_put, parameter: EcomaxParameter, bypass_asyncio_sleep, caplog
) -> None:
    """Test that frame doesn't get dispatched if value is unchanged."""
    assert not parameter.change_pending

    assert not await parameter.set(STATE_OFF, retries=3)
    assert parameter.change_pending
    assert mock_put.await_count == 3
    assert "Timed out while trying to set 'summer_mode' parameter" in caplog.text
    await parameter.set(STATE_OFF)
    mock_put.not_awaited()


@patch("pyplumio.helpers.parameter.Parameter.set")
async def test_binary_parameter_turn_on_off(
    mock_set, parameter: EcomaxBinaryParameter
) -> None:
    """Test that binary parameter can be turned on and off."""
    await parameter.turn_on()
    mock_set.assert_called_once_with(STATE_ON)
    mock_set.reset_mock()
    await parameter.turn_off()
    mock_set.assert_called_once_with(STATE_OFF)
