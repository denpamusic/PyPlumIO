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
)
from pyplumio.helpers.typing import ParameterDataType


@pytest.fixture(name="parameter")
def fixture_parameter(ecomax: EcoMAX) -> BoilerBinaryParameter:
    """Return instance of summer_mode parameter."""
    return BoilerBinaryParameter(
        device=ecomax,
        name="summer_mode",
        value=1,
        min_value=0,
        max_value=1,
    )


def test_parameter_set(parameter: BoilerBinaryParameter) -> None:
    """Test setting parameter."""
    parameter.set(0)
    assert parameter == STATE_OFF

    parameter.set("on")
    assert parameter == 1


def test_parameter_set_out_of_range(parameter: BoilerBinaryParameter) -> None:
    """Test setting parameter with value out of allowed range."""
    with pytest.raises(ValueError):
        parameter.set(39)


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
        name="mix_target_temp",
        value=50,
        min_value=50,
        max_value=80,
        extra=0,
    )
    assert isinstance(parameter.request, SetMixerParameterRequest)


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


@patch("asyncio.Queue.put_nowait")
def test_parameter_request_with_unchanged_value(
    mock_put_nowait, parameter: BoilerParameter
) -> None:
    """Test that frame doesn't get dispatched if value is unchanged."""
    assert not parameter.changed
    parameter.set("off")
    assert parameter.changed
    mock_put_nowait.assert_called_once()
    parameter.set("off")
    mock_put_nowait.not_called()


@patch("pyplumio.helpers.parameter.Parameter.set")
def test_binary_parameter_turn_on_off(
    mock_set, parameter: BoilerBinaryParameter
) -> None:
    """Test that binary parameter can be turned on and off."""
    parameter.turn_on()
    mock_set.assert_called_once_with(STATE_ON)
    mock_set.reset_mock()
    parameter.turn_off()
    mock_set.assert_called_once_with(STATE_OFF)
