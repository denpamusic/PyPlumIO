"""Contains tests for the parameter helper class."""
from unittest.mock import patch

import pytest

from pyplumio.const import STATE_OFF, STATE_ON
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.frames import Request
from pyplumio.helpers.parameter import BinaryParameter, Parameter, ParameterDescription
from pyplumio.helpers.typing import ParameterDataType


class TestParameter(Parameter):
    """Concrete implementation of the parameter class."""

    __test__: bool = False

    @property
    def request(self) -> Request:
        """Return request to change the parameter."""
        return Request()


class TestBinaryParameter(BinaryParameter, TestParameter):
    """Concrete implementation of the binary parameter class."""


@pytest.fixture(name="parameter")
def fixture_parameter(ecomax: EcoMAX) -> Parameter:
    """Return an instance of the parameter."""
    return TestParameter(
        device=ecomax,
        value=1,
        min_value=0,
        max_value=5,
        description=ParameterDescription(name="test_parameter"),
    )


@pytest.fixture(name="binary_parameter")
def fixture_binary_parameter(ecomax: EcoMAX) -> BinaryParameter:
    """Return an instance of the parameter."""
    return TestBinaryParameter(
        device=ecomax,
        value=STATE_OFF,
        min_value=STATE_OFF,
        max_value=STATE_ON,
        description=ParameterDescription(name="test_binary_parameter"),
    )


async def test_parameter_values(parameter: Parameter) -> None:
    """Test the parameter values."""
    assert parameter.value == 1
    assert parameter.min_value == 0
    assert parameter.max_value == 5


def test_base_parameter_request(ecomax: EcoMAX) -> None:
    """Test that base class request throws not implemented error."""
    parameter = Parameter(
        device=ecomax,
        value=1,
        min_value=0,
        max_value=5,
        description=ParameterDescription(name="test_parameter"),
    )

    with pytest.raises(NotImplementedError):
        assert not parameter.request


@patch("pyplumio.devices.ecomax.EcoMAX.subscribe_once")
async def test_parameter_set(
    mock_subscribe_once, parameter: Parameter, bypass_asyncio_sleep
) -> None:
    """Test setting parameter."""
    await parameter.set(5)
    assert parameter == 5
    mock_subscribe_once.assert_called_once()
    callback = mock_subscribe_once.call_args.args[1]
    assert parameter.is_changed
    await callback(parameter)
    assert not parameter.is_changed
    with patch("pyplumio.helpers.parameter.Parameter.is_changed", False):
        assert await parameter.set(3)

    assert parameter == 3


async def test_parameter_set_out_of_range(parameter: Parameter) -> None:
    """Test setting a parameter with value out of allowed range."""
    with pytest.raises(ValueError):
        await parameter.set(39)


def test_parameter_relational(parameter: Parameter):
    """Test a parameter subtraction."""
    assert (parameter - 1) == 0
    assert (parameter + 1) == 2
    assert (parameter * 5) == 5
    assert (parameter / 1) == 1
    assert (parameter // 1) == 1


def test_parameter_compare(parameter: Parameter) -> None:
    """Test a parameter comparison."""
    assert parameter == 1
    parameter_tuple: ParameterDataType = (1, 0, 5)
    assert parameter == parameter_tuple
    assert not parameter != parameter_tuple
    assert parameter < 2
    assert parameter > 0
    assert 0 <= parameter <= 1


def test_parameter_int(parameter: Parameter) -> None:
    """Test a parameter conversion to integer."""
    assert int(parameter) == 1


def test_parameter_repr(parameter: Parameter) -> None:
    """Test a parameter representation."""
    assert repr(parameter) == (
        "TestParameter(device=EcoMAX, "
        + "description=ParameterDescription(name='test_parameter'), "
        + "value=1, min_value=0, max_value=5)"
    )


@patch("asyncio.Queue.put")
async def test_parameter_request_with_unchanged_value(
    mock_put, parameter: Parameter, bypass_asyncio_sleep, caplog
) -> None:
    """Test that frame doesn't get dispatched if it's
    value is not changed."""
    assert not parameter.is_changed
    assert not await parameter.set(5, retries=3)
    assert parameter.is_changed
    assert mock_put.await_count == 3
    mock_put.reset_mock()
    assert "Timed out while trying to set 'test_parameter' parameter" in caplog.text
    await parameter.set(5)
    mock_put.assert_not_awaited()


@patch("pyplumio.helpers.parameter.Parameter.set")
async def test_binary_parameter_turn_on_off(
    mock_set, binary_parameter: BinaryParameter
) -> None:
    """Test that binary parameter can be turned on and off."""
    await binary_parameter.turn_on()
    mock_set.assert_called_once_with(STATE_ON)
    mock_set.reset_mock()
    await binary_parameter.turn_off()
    mock_set.assert_called_once_with(STATE_OFF)


async def test_binary_parameter_values(binary_parameter: BinaryParameter) -> None:
    """Test the binary parameter values."""
    assert binary_parameter.value == STATE_OFF
    assert binary_parameter.min_value == STATE_OFF
    assert binary_parameter.max_value == STATE_ON
