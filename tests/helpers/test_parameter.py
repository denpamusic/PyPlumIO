"""Contains tests for the parameter helper class."""

from copy import copy
from unittest.mock import Mock, patch

import pytest

from pyplumio.const import BYTE_UNDEFINED, STATE_OFF, STATE_ON, UnitOfMeasurement
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.helpers.parameter import (
    Number,
    NumberDescription,
    Parameter,
    ParameterDescription,
    ParameterValues,
    Switch,
    SwitchDescription,
    check_parameter,
)


@pytest.fixture(name="number")
def fixture_number(ecomax: EcoMAX) -> Number:
    """Return a numerical parameter object."""
    return Number(
        device=ecomax,
        values=ParameterValues(value=1, min_value=0, max_value=5),
        description=NumberDescription(
            name="test_number", unit_of_measurement=UnitOfMeasurement.CELSIUS
        ),
    )


@pytest.fixture(name="switch")
def fixture_switch(ecomax: EcoMAX) -> Switch:
    """Return a switch object."""
    return Switch(
        device=ecomax,
        values=ParameterValues(value=0, min_value=0, max_value=1),
        description=SwitchDescription(name="test_switch"),
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


@pytest.mark.parametrize(
    ("handler", "description", "values"),
    [
        (
            Number,
            NumberDescription(
                name="test_number", unit_of_measurement=UnitOfMeasurement.CELSIUS
            ),
            ParameterValues(value=3, min_value=0, max_value=5),
        ),
        (
            Switch,
            SwitchDescription(name="test_switch"),
            ParameterValues(value=0, min_value=0, max_value=1),
        ),
    ],
)
def test_create_or_update_parameter(
    ecomax: EcoMAX,
    handler: type[Parameter],
    description: ParameterDescription,
    values: ParameterValues,
) -> None:
    """Test creating or updating a parameter."""
    with patch("pyplumio.helpers.parameter.Parameter.update") as mock_update:
        parameter = handler.create_or_update(
            device=ecomax, description=description, values=values
        )

    mock_update.assert_not_called()
    assert isinstance(parameter, handler)

    # Test updating an existing parameter.
    ecomax.data[description.name] = parameter
    with patch("pyplumio.helpers.parameter.Parameter.update") as mock_update:
        handler.create_or_update(device=ecomax, description=description, values=values)

    mock_update.assert_called_once()


async def test_number_values(number: Number) -> None:
    """Test the number values."""
    assert number.value == 1
    assert number.min_value == 0
    assert number.max_value == 5


async def test_switch_value(switch: Switch) -> None:
    """Test the switch values."""
    assert switch.value == STATE_OFF
    assert switch.min_value == STATE_OFF
    assert switch.max_value == STATE_ON


async def test_number_set(number: Number, bypass_asyncio_sleep) -> None:
    """Test setting a number."""
    retries = 5
    with patch(
        "pyplumio.helpers.parameter.Number.create_refresh_request"
    ) as mock_create_refresh_request:
        await number.set(5, retries=retries)

    assert not number.is_tracking_changes
    assert mock_create_refresh_request.await_count == retries
    number.update(ParameterValues(value=5, min_value=0, max_value=5))
    assert number == 5
    assert not number.pending_update
    with patch("pyplumio.helpers.parameter.Parameter.pending_update", False):
        assert await number.set(3)

    assert number == 3

    # Test out of range.
    with pytest.raises(ValueError):
        await number.set(39)


async def test_switch_set(switch: Switch, bypass_asyncio_sleep) -> None:
    """Test setting a number."""
    retries = 5
    with patch(
        "pyplumio.helpers.parameter.Switch.create_refresh_request"
    ) as mock_create_refresh_request:
        await switch.set(STATE_ON, retries=retries)

    assert not switch.is_tracking_changes
    assert mock_create_refresh_request.await_count == retries
    switch.update(ParameterValues(value=1, min_value=0, max_value=1))
    assert switch == 1
    assert not switch.pending_update
    with patch("pyplumio.helpers.parameter.Parameter.pending_update", False):
        assert await switch.set(STATE_OFF)

    assert switch == 0


@patch("pyplumio.devices.Device.create_task")
@patch("pyplumio.helpers.parameter.Number.set", new_callable=Mock)
async def test_number_set_nowait(mock_set, mock_create_task, number: Number):
    """Test setting a number without waiting for result."""
    number.set_nowait(1)
    await number.device.wait_until_done()
    mock_create_task.assert_called_once()
    mock_set.assert_called_once_with(1, 5, 5.0)


@patch("pyplumio.devices.Device.create_task")
@patch("pyplumio.helpers.parameter.Switch.set", new_callable=Mock)
async def test_switch_set_nowait(mock_set, mock_create_task, switch: Switch):
    """Test setting a number without waiting for result."""
    switch.set_nowait(STATE_ON)
    await switch.device.wait_until_done()
    mock_create_task.assert_called_once()
    mock_set.assert_called_once_with(STATE_ON, 5, 5.0)


def test_number_update(number: Number) -> None:
    """Test updating a number values."""
    number.update(ParameterValues(value=1, min_value=0, max_value=5))
    assert number.value == 1


def test_switch_update(switch: Switch) -> None:
    """Test updating a switch values."""
    switch.update(ParameterValues(value=1, min_value=0, max_value=1))
    assert switch.value == STATE_ON


def test_number_relational(number: Number):
    """Test number relational methods."""
    new_number = copy(number)
    assert number == new_number
    assert (number - 1) == 0
    new_values = ParameterValues(value=1, min_value=0, max_value=5)
    number.update(new_values)
    assert number == new_values
    assert (number + 1) == 2
    assert (number * 5) == 5
    assert (number / 1) == 1
    assert (number // 1) == 1
    assert number.__eq__("cola") is NotImplemented


def test_switch_relational(switch: Switch):
    """Test switch relational methods."""
    new_switch = copy(switch)
    assert switch == new_switch
    new_values = ParameterValues(value=1, min_value=0, max_value=1)
    assert (switch + 1) == 1
    switch.update(new_values)
    assert switch == new_values
    assert (switch - 1) == 0
    assert (switch * 0) == 0
    assert (switch / 1) == 1
    assert (switch // 1) == 1
    assert switch.__eq__("cola") is NotImplemented


def test_number_compare(number: Number) -> None:
    """Test number comparison."""
    assert number == 1
    values = ParameterValues(value=1, min_value=0, max_value=5)
    assert number == values
    assert not number != values
    assert number < 2
    assert number > 0
    assert 0 <= number <= 1


def test_switch_compare(switch: Switch) -> None:
    """Test switch comparison."""
    assert switch == 0
    values = ParameterValues(value=0, min_value=0, max_value=1)
    assert switch == values
    assert not switch != values
    assert switch < 2
    switch.update(ParameterValues(value=1, min_value=0, max_value=0))
    assert switch > 0
    assert 0 <= switch <= 1


def test_number_int(number: Number) -> None:
    """Test number conversion to an integer."""
    assert int(number) == 1


def test_switch_int(switch: Switch) -> None:
    """Test switch conversion to an integer."""
    assert int(switch) == 0


def test_number_repr(number: Number) -> None:
    """Test a number representation."""
    assert repr(number) == (
        "Number(device=EcoMAX, "
        "description=NumberDescription(name='test_number', "
        "unit_of_measurement=<UnitOfMeasurement.CELSIUS: '°C'>), "
        "values=ParameterValues(value=1, min_value=0, max_value=5), "
        "index=0)"
    )


def test_switch_repr(switch: Switch) -> None:
    """Test a number representation."""
    assert repr(switch) == (
        "Switch(device=EcoMAX, "
        "description=SwitchDescription(name='test_switch'), "
        "values=ParameterValues(value=0, min_value=0, max_value=1), "
        "index=0)"
    )


@patch("asyncio.Queue.put")
async def test_number_request_with_unchanged_value(
    mock_put, number: Number, bypass_asyncio_sleep, caplog
) -> None:
    """Test that a frame doesn't get dispatched if it's value is unchanged."""
    assert not number.pending_update
    assert not await number.set(5, retries=3)
    assert number.pending_update
    assert mock_put.await_count == 6  # type: ignore [unreachable]
    mock_put.reset_mock()
    assert "Timed out while trying to set 'test_number' parameter" in caplog.text
    await number.set(5)
    mock_put.assert_not_awaited()


@patch("asyncio.Queue.put")
async def test_switch_request_with_unchanged_value(
    mock_put, switch: Switch, bypass_asyncio_sleep, caplog
) -> None:
    """Test that a frame doesn't get dispatched if it's value is unchanged."""
    assert not switch.pending_update
    assert not await switch.set(True, retries=3)
    assert switch.pending_update
    assert mock_put.await_count == 6  # type: ignore [unreachable]
    mock_put.reset_mock()
    assert "Timed out while trying to set 'test_switch' parameter" in caplog.text
    await switch.set(True)
    mock_put.assert_not_awaited()


@patch("pyplumio.helpers.parameter.Switch.set")
async def test_switch_turn_on(mock_set, switch: Switch) -> None:
    """Test that switch can be turned on."""
    await switch.turn_on()
    mock_set.assert_called_once_with(STATE_ON)


@patch("pyplumio.helpers.parameter.Switch.set")
async def test_switch_turn_off(mock_set, switch: Switch) -> None:
    """Test that switch can be turned off."""
    await switch.turn_off()
    mock_set.assert_called_once_with(STATE_OFF)


@patch("pyplumio.helpers.parameter.Switch.set_nowait")
async def test_binary_parameter_turn_on_nowait(mock_set_nowait, switch: Switch) -> None:
    """Test that a switch can be turned on without waiting."""
    switch.turn_on_nowait()
    mock_set_nowait.assert_called_once_with(STATE_ON)


@patch("pyplumio.helpers.parameter.Switch.set_nowait")
async def test_switch_turn_off_nowait(mock_set_nowait, switch: Switch) -> None:
    """Test that a switch can be turned off without waiting."""
    switch.turn_off_nowait()
    mock_set_nowait.assert_called_once_with(STATE_OFF)
