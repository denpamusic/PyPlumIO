"""Contains tests for parameter."""


from unittest.mock import patch

import pytest

from pyplumio.devices.ecomax import EcoMAX
from pyplumio.frames.requests import (
    BoilerControlRequest,
    SetBoilerParameterRequest,
    SetMixerParameterRequest,
)
from pyplumio.helpers.parameter import (
    STATE_OFF,
    STATE_ON,
    BoilerBinaryParameter,
    BoilerParameter,
    MixerParameter,
    ScheduleParameter,
)
from pyplumio.helpers.typing import ParameterDataType


@pytest.fixture(name="parameter")
def fixture_parameter(ecomax: EcoMAX) -> BoilerBinaryParameter:
    """Return instance of summer_mode parameter."""
    parameter = BoilerBinaryParameter(
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
    mock_subscribe_once, parameter: BoilerBinaryParameter, bypass_asyncio_sleep
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
        assert await parameter.set("on")

    assert parameter == 1


async def test_parameter_set_out_of_range(parameter: BoilerBinaryParameter) -> None:
    """Test setting parameter with value out of allowed range."""
    with pytest.raises(ValueError):
        await parameter.set(39)


def test_parameter_relational(parameter: BoilerBinaryParameter):
    """Test parameter subtraction."""
    assert (parameter - 1) == 0
    assert (parameter + 1) == 2
    assert (parameter * 5) == 5
    assert (parameter / 1) == 1
    assert (parameter // 1) == 1


def test_parameter_compare(parameter: BoilerBinaryParameter) -> None:
    """Test parameter comparison."""
    assert parameter == 1
    parameter_tuple: ParameterDataType = (1, 0, 1)
    assert parameter == parameter_tuple
    assert not parameter != parameter_tuple
    assert parameter < 2
    assert parameter > 0
    assert 0 <= parameter <= 1


def test_parameter_int(parameter: BoilerBinaryParameter) -> None:
    """Test conversion to integer."""
    assert int(parameter) == 1


def test_parameter_repr(parameter: BoilerBinaryParameter) -> None:
    """Test parameter serilizable representation."""
    assert repr(parameter) == (
        "BoilerBinaryParameter(device=EcoMAX, name=summer_mode, value=1, "
        + "min_value=0, max_value=1, extra=None)"
    )


def test_parameter_request(parameter: BoilerBinaryParameter) -> None:
    """Test parameter set request instance."""
    assert isinstance(parameter.request, SetBoilerParameterRequest)


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
    """Test boiler control parameter request instance."""
    parameter = BoilerParameter(
        device=ecomax,
        name="boiler_control",
        value=1,
        min_value=0,
        max_value=1,
    )
    assert isinstance(parameter.request, BoilerControlRequest)


@patch("asyncio.Queue.put")
async def test_parameter_request_with_unchanged_value(
    mock_put, parameter: BoilerParameter, bypass_asyncio_sleep, caplog
) -> None:
    """Test that frame doesn't get dispatched if value is unchanged."""
    assert not parameter.change_pending

    assert not await parameter.set("off", retries=3)
    assert parameter.change_pending
    assert mock_put.await_count == 3
    assert "Timed out while trying to set 'summer_mode' parameter" in caplog.text
    await parameter.set("off")
    mock_put.not_awaited()


@patch("pyplumio.helpers.parameter.Parameter.set")
async def test_binary_parameter_turn_on_off(
    mock_set, parameter: BoilerBinaryParameter
) -> None:
    """Test that binary parameter can be turned on and off."""
    await parameter.turn_on()
    mock_set.assert_called_once_with(STATE_ON)
    mock_set.reset_mock()
    await parameter.turn_off()
    mock_set.assert_called_once_with(STATE_OFF)
