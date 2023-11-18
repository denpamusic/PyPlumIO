"""Contains tests for the parameter helper class."""
from unittest.mock import Mock, patch

import pytest

from pyplumio.const import BYTE_UNDEFINED, STATE_OFF, STATE_ON, UnitOfMeasurement
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.frames import Request
from pyplumio.helpers.parameter import (
    BinaryParameter,
    Parameter,
    ParameterDescription,
    ParameterValues,
    check_parameter,
)


class TestParameter(Parameter):
    """Represents a concrete implementation of the parameter class."""

    __test__: bool = False

    @property
    def request(self) -> Request:
        """A request to change the parameter."""
        return Request()


class TestBinaryParameter(BinaryParameter, TestParameter):
    """Represents a concrete implementation of the binary parameter
    class.
    """


@pytest.fixture(name="parameter")
def fixture_parameter(ecomax: EcoMAX) -> Parameter:
    """Return a parameter object."""
    return TestParameter(
        device=ecomax,
        values=ParameterValues(value=1, min_value=0, max_value=5),
        description=ParameterDescription(
            name="test_parameter", unit_of_measurement=UnitOfMeasurement.CELSIUS
        ),
    )


@pytest.fixture(name="binary_parameter")
def fixture_binary_parameter(ecomax: EcoMAX) -> BinaryParameter:
    """Return a binary parameter object."""
    return TestBinaryParameter(
        device=ecomax,
        values=ParameterValues(value=0, min_value=0, max_value=1),
        description=ParameterDescription(name="test_binary_parameter"),
    )


def test_check_parameter_valid() -> None:
    """Test checking if parameter is valid."""
    assert check_parameter(
        bytearray([BYTE_UNDEFINED, 0xFE, BYTE_UNDEFINED, BYTE_UNDEFINED])
    )


def test_check_parameter_invalid() -> None:
    """Test checking if parameter is invalid."""
    assert not check_parameter(
        bytearray([BYTE_UNDEFINED, BYTE_UNDEFINED, BYTE_UNDEFINED, BYTE_UNDEFINED])
    )


async def test_parameter_values(parameter: Parameter) -> None:
    """Test the parameter values."""
    assert parameter.value == 1
    assert parameter.min_value == 0
    assert parameter.max_value == 5


def test_base_parameter_request(ecomax: EcoMAX) -> None:
    """Test that a base class request throws not implemented error."""
    parameter = Parameter(
        device=ecomax,
        values=ParameterValues(value=1, min_value=0, max_value=5),
        description=ParameterDescription(name="test_parameter"),
    )

    with pytest.raises(NotImplementedError):
        assert not parameter.request


@patch("pyplumio.devices.ecomax.EcoMAX.subscribe_once")
async def test_parameter_set(
    mock_subscribe_once, parameter: Parameter, bypass_asyncio_sleep
) -> None:
    """Test setting a parameter."""
    await parameter.set(5)
    assert parameter == 5
    mock_subscribe_once.assert_called_once()
    callback = mock_subscribe_once.call_args.args[1]
    assert parameter.pending_update
    await callback(parameter)
    assert not parameter.pending_update
    with patch("pyplumio.helpers.parameter.Parameter.pending_update", False):
        assert await parameter.set(3)

    assert parameter == 3


@patch("pyplumio.devices.Device.create_task")
@patch("pyplumio.helpers.parameter.Parameter.set", new_callable=Mock)
async def test_parameter_set_nowait(mock_set, mock_create_task, parameter: Parameter):
    """Test setting a parameter without waiting for result."""
    parameter.set_nowait(1)
    await parameter.device.wait_until_done()
    mock_create_task.assert_called_once()
    mock_set.assert_called_once_with(1, 5)


async def test_parameter_set_out_of_range(parameter: Parameter) -> None:
    """Test setting a parameter with value out of allowed range."""
    with pytest.raises(ValueError):
        await parameter.set(39)


def test_parameter_relational(parameter: Parameter):
    """Test parameter relational methods."""
    assert (parameter - 1) == 0
    assert (parameter + 1) == 2
    assert (parameter * 5) == 5
    assert (parameter / 1) == 1
    assert (parameter // 1) == 1


def test_parameter_compare(parameter: Parameter) -> None:
    """Test parameter comparison."""
    assert parameter == 1
    parameter_values = ParameterValues(value=1, min_value=0, max_value=5)
    assert parameter == parameter_values
    assert not parameter != parameter_values
    assert parameter < 2
    assert parameter > 0
    assert 0 <= parameter <= 1


def test_parameter_int(parameter: Parameter) -> None:
    """Test parameter conversion to an integer."""
    assert int(parameter) == 1


def test_parameter_repr(parameter: Parameter) -> None:
    """Test a parameter representation."""
    assert repr(parameter) == (
        "TestParameter(device=EcoMAX, "
        "values=ParameterValues(value=1, min_value=0, max_value=5), "
        "description=ParameterDescription(name='test_parameter', "
        "unit_of_measurement=<UnitOfMeasurement.CELSIUS: '°C'>), "
        "index=0)"
    )


@patch("asyncio.Queue.put")
async def test_parameter_request_with_unchanged_value(
    mock_put, parameter: Parameter, bypass_asyncio_sleep, caplog
) -> None:
    """Test that a frame doesn't get dispatched if it's
    value is unchanged."""
    assert not parameter.pending_update
    assert not await parameter.set(5, retries=3)
    assert parameter.pending_update
    assert mock_put.await_count == 3
    mock_put.reset_mock()
    assert "Timed out while trying to set 'test_parameter' parameter" in caplog.text
    await parameter.set(5)
    mock_put.assert_not_awaited()


@patch("pyplumio.helpers.parameter.BinaryParameter.set")
async def test_binary_parameter_turn_on(
    mock_set, binary_parameter: BinaryParameter
) -> None:
    """Test that a binary parameter can be turned on."""
    await binary_parameter.turn_on()
    mock_set.assert_called_once_with(STATE_ON)


@patch("pyplumio.helpers.parameter.BinaryParameter.set")
async def test_binary_parameter_turn_off(
    mock_set, binary_parameter: BinaryParameter
) -> None:
    """Test that a binary parameter can be turned off."""
    await binary_parameter.turn_off()
    mock_set.assert_called_once_with(STATE_OFF)


@patch("pyplumio.helpers.parameter.BinaryParameter.set_nowait")
async def test_binary_parameter_turn_on_nowait(
    mock_set_nowait, binary_parameter: BinaryParameter
) -> None:
    """Test that a binary parameter can be turned on without waiting."""
    binary_parameter.turn_on_nowait()
    mock_set_nowait.assert_called_once_with(STATE_ON)


@patch("pyplumio.helpers.parameter.BinaryParameter.set_nowait")
async def test_binary_parameter_turn_off_nowait(
    mock_set_nowait, binary_parameter: BinaryParameter
) -> None:
    """Test that a binary parameter can be turned off without
    waiting.
    """
    binary_parameter.turn_off_nowait()
    mock_set_nowait.assert_called_once_with(STATE_OFF)


async def test_binary_parameter_values(binary_parameter: BinaryParameter) -> None:
    """Test a binary parameter values."""
    assert binary_parameter.value == STATE_OFF
    assert binary_parameter.min_value == STATE_OFF
    assert binary_parameter.max_value == STATE_ON
