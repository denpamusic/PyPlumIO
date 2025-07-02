"""Contains tests for the parameter descriptors."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from pyplumio.const import BYTE_UNDEFINED, STATE_OFF, STATE_ON, State, UnitOfMeasurement
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.frames import Request
from pyplumio.parameters import (
    Number,
    NumberDescription,
    Parameter,
    ParameterDescription,
    ParameterValues,
    Switch,
    SwitchDescription,
    is_valid_parameter,
)


@pytest.fixture(name="number")
def fixture_number(ecomax: EcoMAX) -> Number:
    """Numeric parameter instance.

    Returns a Number object for testing.
    """
    return Number(
        device=ecomax,
        values=ParameterValues(value=1, min_value=0, max_value=5),
        description=NumberDescription(
            name="test_number", unit_of_measurement=UnitOfMeasurement.CELSIUS
        ),
    )


@pytest.fixture(name="switch")
def fixture_switch(ecomax: EcoMAX) -> Switch:
    """Switch instance.

    Returns a Switch object for testing.
    """
    return Switch(
        device=ecomax,
        values=ParameterValues(value=0, min_value=0, max_value=1),
        description=SwitchDescription(name="test_switch"),
    )


@pytest.mark.parametrize(
    ("data", "expected_result"),
    [
        (bytearray([BYTE_UNDEFINED, 0xFE, BYTE_UNDEFINED, BYTE_UNDEFINED]), True),
        (
            bytearray([BYTE_UNDEFINED, BYTE_UNDEFINED, BYTE_UNDEFINED, BYTE_UNDEFINED]),
            False,
        ),
    ],
)
def test_is_valid_parameter(data: bytearray, expected_result: bool) -> None:
    """Test is_valid_parameter.

    Checks if parameter data is valid.
    """
    assert is_valid_parameter(data) is expected_result


class DummyParameter(Parameter):
    """Dummy parameter for testing."""

    def _pack_value(self, value: Any) -> int:
        """Pack the parameter value."""
        return int(value)

    def _unpack_value(self, value: Any):
        """Unpack the parameter value."""

    def validate(self, value: Any):
        """Validate a parameter value."""

    @property
    def value(self) -> Any:
        """Return the value."""

    @property
    def min_value(self) -> Any:
        """Return the minimum allowed value."""

    @property
    def max_value(self) -> Any:
        """Return the maximum allowed value."""

    @property
    async def create_request(self):
        """Create a request to change the parameter."""


@pytest.fixture(name="parameter")
def fixture_parameter(ecomax: EcoMAX) -> Parameter:
    """Parameter instance.

    Returns a DummyParameter object for testing.
    """
    return DummyParameter(
        device=ecomax,
        values=ParameterValues(value=6, min_value=0, max_value=10),
        description=ParameterDescription(name="test_param"),
    )


class TestParameter:
    """Tests for Parameter class.

    Verifies representation, math, equality, copy, set, and update.
    """

    def test_repr(self, parameter: Parameter) -> None:
        """Test __repr__.

        Checks parameter representation.
        """
        assert repr(parameter) == (
            f"DummyParameter(device={parameter.device}, "
            "description=ParameterDescription(name='test_param', optimistic=False), "
            "values=ParameterValues(value=6, min_value=0, max_value=10), "
            "index=0)"
        )

    def test_int(self, parameter: Parameter) -> None:
        """Test __int__.

        Checks parameter conversion to int.
        """
        result = int(parameter)
        assert result == 6
        assert isinstance(result, int)

    def test_hash(self, parameter: Parameter) -> None:
        """Test __hash__.

        Checks parameter hashing.
        """
        assert hash(parameter) == hash(
            frozenset({("value", 6), ("min_value", 0), ("max_value", 10)})
        )

    @pytest.mark.parametrize(
        ("func_name", "other", "expected_result", "expected_type"),
        [
            ("__add__", "Parameter", 12, int),
            ("__add__", ParameterValues(1, 0, 10), 7, int),
            ("__add__", 10, 16, int),
            ("__add__", 2.1, 8, int),
            ("__add__", "mango", NotImplemented, None),
            ("__sub__", "Parameter", 0, int),
            ("__sub__", ParameterValues(3, 0, 10), 3, int),
            ("__sub__", 4, 2, int),
            ("__sub__", 4.1, 2, int),
            ("__sub__", None, NotImplemented, None),
            ("__truediv__", "Parameter", 1, float),
            ("__truediv__", ParameterValues(3, 0, 10), 2, float),
            ("__truediv__", 3, 2, float),
            ("__truediv__", 2.2, 3, float),
            ("__floordiv__", "Parameter", 1, int),
            ("__floordiv__", ParameterValues(2, 0, 10), 3, int),
            ("__floordiv__", 4, 1, int),
            ("__floordiv__", 1.5, 6, int),
            ("__floordiv__", True, 6, None),
            ("__mul__", "Parameter", 36, int),
            ("__mul__", ParameterValues(2, 0, 10), 12, int),
            ("__mul__", 3, 18, int),
            ("__mul__", 2.5, 12, int),
            ("__mul__", object, NotImplemented, None),
        ],
    )
    def test_math(
        self,
        func_name: str,
        other: Any,
        expected_result: int,
        expected_type: type,
        parameter: Parameter,
    ) -> None:
        """Test math operations.

        Checks addition, subtraction, division, multiplication, etc.
        """
        if other == "Parameter":
            other = parameter

        func = getattr(parameter, func_name)
        result = func(other)
        assert result == expected_result
        if expected_type:
            assert isinstance(result, expected_type)

    @pytest.mark.parametrize(
        ("func_name", "other", "expected_result"),
        [
            ("__eq__", "Parameter", True),
            ("__eq__", ParameterValues(7, 1, 10), False),
            ("__eq__", ParameterValues(6, 2, 10), True),
            ("__eq__", 6, True),
            ("__eq__", 2.5, False),
            ("__eq__", True, False),
            ("__eq__", "banana", NotImplemented),
            ("__ge__", "Parameter", True),
            ("__ge__", ParameterValues(6, 1, 10), True),
            ("__ge__", ParameterValues(9, 2, 10), False),
            ("__ge__", 6, True),
            ("__ge__", 2.5, True),
            ("__ge__", True, True),
            ("__ge__", None, NotImplemented),
            ("__gt__", "Parameter", False),
            ("__gt__", ParameterValues(4, 1, 10), True),
            ("__gt__", ParameterValues(6, 2, 10), False),
            ("__gt__", 7, False),
            ("__gt__", 2.5, True),
            ("__gt__", True, True),
            ("__gt__", bytearray(), NotImplemented),
            ("__le__", "Parameter", True),
            ("__le__", ParameterValues(6, 1, 10), True),
            ("__le__", ParameterValues(4, 2, 10), False),
            ("__le__", 8, True),
            ("__le__", 2.5, False),
            ("__le__", True, False),
            ("__le__", b"", NotImplemented),
            ("__lt__", "Parameter", False),
            ("__lt__", ParameterValues(7, 1, 10), True),
            ("__lt__", ParameterValues(4, 2, 10), False),
            ("__lt__", 7, True),
            ("__lt__", 2.5, False),
            ("__lt__", True, False),
            ("__lt__", object, NotImplemented),
        ],
    )
    def test_eq(
        self,
        func_name: str,
        other: Any,
        expected_result: bool,
        parameter: Parameter,
    ) -> None:
        """Test equality and comparison.

        Checks eq, ge, gt, le, lt.
        """
        if other == "Parameter":
            other = parameter

        func = getattr(parameter, func_name)
        assert func(other) is expected_result

    def test_copy(self, parameter: Parameter) -> None:
        """Test __copy__.

        Checks shallow copying of parameter.
        """
        parameter_copy = parameter.__copy__()
        assert parameter_copy.values is not parameter.values

    @patch.object(DummyParameter, "validate")
    @patch.object(DummyParameter, "create_request", new_callable=AsyncMock)
    @patch("asyncio.Queue.put")
    @pytest.mark.parametrize("nowait", [False, True])
    async def test_set(
        self,
        mock_put,
        mock_create_request,
        mock_validate,
        parameter: Parameter,
        nowait: bool,
    ) -> None:
        """Test set.

        Checks setting a parameter with and without waiting.
        """
        if nowait:
            parameter.set_nowait(4)
            await parameter.device.wait_until_done()
        else:
            mock_update_pending = AsyncMock(spec=asyncio.Event)
            mock_update_done = AsyncMock(spec=asyncio.Event)
            mock_update_done.is_set = Mock(return_value=True)
            with (
                patch.object(DummyParameter, "update_pending", mock_update_pending),
                patch.object(DummyParameter, "update_done", mock_update_done),
            ):
                result = await parameter.set(4)

            assert result is True
            mock_update_done.clear.assert_called_once()
            mock_update_pending.set.assert_called_once()

        assert parameter == 4
        mock_validate.assert_called_once_with(4)
        mock_create_request.assert_awaited_once()
        mock_put.assert_awaited_once_with(mock_create_request.return_value)

    @patch.object(DummyParameter, "validate")
    @patch.object(DummyParameter, "create_request", new_callable=AsyncMock)
    @patch("asyncio.Queue.put")
    @pytest.mark.parametrize("nowait", [False, True])
    async def test_set_unchanged(
        self,
        mock_put,
        mock_create_request,
        mock_validate,
        parameter: Parameter,
        nowait: bool,
    ) -> None:
        """Test set with unchanged value.

        Checks setting a parameter when value is unchanged.
        """
        if nowait:
            parameter.set_nowait(6)
            await parameter.device.wait_until_done()
        else:
            result = await parameter.set(6)
            assert result is True

        assert parameter == 6
        mock_validate.assert_called_once_with(6)
        mock_create_request.assert_not_awaited()
        mock_put.assert_not_awaited()

    @patch.object(DummyParameter, "validate")
    @patch.object(DummyParameter, "create_request", new_callable=AsyncMock)
    @patch("asyncio.Queue.put")
    @pytest.mark.parametrize(
        (
            "event_side_effect",
            "retries",
            "expected_result",
            "expected_call_count",
            "log_message",
        ),
        [
            ((False, True), 5, True, 2, None),
            (
                (False, False),
                2,
                False,
                2,
                "Unable to confirm update of 'test_param' parameter after 2 retries",
            ),
        ],
    )
    async def test_set_with_retries(
        self,
        mock_put,
        mock_create_request,
        mock_validate,
        parameter: Parameter,
        caplog,
        event_side_effect: tuple[bool, ...],
        retries: int,
        expected_result: bool,
        expected_call_count: int,
        log_message: str | None,
    ) -> None:
        """Test set without retries.

        Checks setting a parameter with and without retries.
        """
        parameter.description = ParameterDescription(name="test_param")
        mock_update_pending = AsyncMock(spec=asyncio.Event)
        mock_update_done = AsyncMock(spec=asyncio.Event)
        mock_update_done.is_set = Mock(side_effect=event_side_effect)

        with (
            patch.object(DummyParameter, "update_pending", mock_update_pending),
            patch.object(DummyParameter, "update_done", mock_update_done),
        ):
            result = await parameter.set(5, retries=retries)

        assert result is expected_result
        assert parameter == 5
        mock_create_request.assert_awaited_once()
        mock_validate.assert_called_once_with(5)
        assert mock_put.call_count == expected_call_count

        if log_message:
            assert log_message in caplog.text

    @patch.object(DummyParameter, "validate")
    @patch.object(DummyParameter, "create_request", new_callable=AsyncMock)
    @patch("asyncio.Queue.put")
    @patch("asyncio.Event.set")
    async def test_set_optimistic(
        self,
        mock_set,
        mock_put,
        mock_create_request,
        mock_validate,
        parameter: Parameter,
    ) -> None:
        """Test set without retries.

        Checks setting a parameter with and without retries.
        """
        parameter.description = ParameterDescription(name="test_param", optimistic=True)
        result = await parameter.set(5, retries=3)
        assert result is True
        assert parameter == 5
        assert parameter.update_pending.is_set() is False
        mock_validate.assert_called_once_with(5)
        mock_put.assert_awaited_once_with(mock_create_request.return_value)
        mock_set.assert_not_called()

    @pytest.mark.usefixtures("skip_asyncio_events")
    @patch.object(DummyParameter, "create_request", new_callable=AsyncMock)
    async def test_update(self, mock_create_request, parameter: Parameter) -> None:
        """Test update.

        Checks updating a parameter.
        """
        await parameter.set(5)
        parameter_values = ParameterValues(value=5, min_value=1, max_value=10)
        parameter.update(parameter_values)
        assert parameter.values == parameter_values
        mock_create_request.assert_awaited_once()

    def test_create_or_update_parameter(self, ecomax: EcoMAX) -> None:
        """Test create_or_update.

        Checks creating or updating a parameter.
        """
        description = ParameterDescription(name="test")
        values = ParameterValues(value=3, min_value=0, max_value=5)
        with patch("pyplumio.parameters.Parameter.update") as mock_update:
            parameter = DummyParameter.create_or_update(
                device=ecomax, description=description, values=values
            )

        mock_update.assert_not_called()
        assert isinstance(parameter, DummyParameter)

        # Test updating an existing parameter.
        ecomax.data[description.name] = parameter
        with patch("pyplumio.parameters.Parameter.update") as mock_update:
            DummyParameter.create_or_update(
                device=ecomax, description=description, values=values
            )

        mock_update.assert_called_once()


class TestNumber:
    """Tests for Number class.

    Verifies value, validation, set, and request creation.
    """

    def test_values(self, number: Number) -> None:
        """Test values.

        Checks number value, min, and max.
        """
        assert number.value == 1
        assert number.min_value == 0
        assert number.max_value == 5

    def test_validate(self, number: Number) -> None:
        """Test validate.

        Checks number validation.
        """
        assert number.validate(2) is True

        with pytest.raises(ValueError, match="The value must be between"):
            number.validate(6)

        with pytest.raises(ValueError, match="value must be adjusted in increments"):
            number.validate(2.1)

    @patch("pyplumio.parameters.Parameter.set")
    async def test_set(self, mock_set, number: Number) -> None:
        """Test set.

        Checks setting a number.
        """
        await number.set(5)
        mock_set.assert_awaited_once_with(5, retries=0, timeout=5.0)

    @patch("pyplumio.parameters.Parameter.set_nowait")
    def test_set_nowait(self, mock_set_nowait, number: Number) -> None:
        """Test set_nowait.

        Checks setting a number without waiting.
        """
        number.set_nowait(5)
        mock_set_nowait.assert_called_once_with(5, retries=0, timeout=5.0)

    async def test_create_request(self, number: Number) -> None:
        """Test create_request.

        Checks creating a number change request.
        """
        assert isinstance(await number.create_request(), Request)


class TestSwitch:
    """Tests for Switch class.

    Verifies value, validation, set, and state changes.
    """

    def test_value(self, switch: Switch) -> None:
        """Test value.

        Checks switch value, min, and max.
        """
        assert switch.value == STATE_OFF
        assert switch.min_value == STATE_OFF
        assert switch.max_value == STATE_ON

    def test_validate(self, switch: Switch) -> None:
        """Test validate.

        Checks switch validation.
        """
        assert switch.validate(STATE_ON) is True

        with pytest.raises(ValueError, match="must be either 'on', 'off' or boolean"):
            switch.validate(2)

    @patch("pyplumio.parameters.Parameter.set")
    @pytest.mark.parametrize("state", [True, False, STATE_ON, STATE_OFF])
    async def test_set(self, mock_set, switch: Switch, state: State | bool) -> None:
        """Test set.

        Checks setting a switch.
        """
        await switch.set(state)
        mock_set.assert_awaited_once_with(state, retries=0, timeout=5.0)

    @patch("pyplumio.parameters.Parameter.set_nowait")
    @pytest.mark.parametrize("state", [True, False, STATE_ON, STATE_OFF])
    def test_set_nowait(
        self, mock_set_nowait, switch: Switch, state: State | bool
    ) -> None:
        """Test set_nowait.

        Checks setting a switch without waiting.
        """
        switch.set_nowait(state)
        mock_set_nowait.assert_called_once_with(state, retries=0, timeout=5.0)

    async def test_create_request(self, switch: Switch) -> None:
        """Test create_request.

        Checks creating a switch change request.
        """
        assert isinstance(await switch.create_request(), Request)

    @patch("pyplumio.parameters.Switch.set")
    async def test_turn_on(self, mock_set, switch: Switch) -> None:
        """Test turn_on.

        Checks turning switch on.
        """
        await switch.turn_on()
        mock_set.assert_called_once_with(STATE_ON)

    @patch("pyplumio.parameters.Switch.set")
    async def test_turn_off(self, mock_set, switch: Switch) -> None:
        """Test turn_off.

        Checks turning switch off.
        """
        await switch.turn_off()
        mock_set.assert_called_once_with(STATE_OFF)

    @patch("pyplumio.parameters.Switch.set_nowait")
    async def test_switch_turn_on_nowait(self, mock_set_nowait, switch: Switch) -> None:
        """Test turn_on_nowait.

        Checks turning switch on without waiting.
        """
        switch.turn_on_nowait()
        mock_set_nowait.assert_called_once_with(STATE_ON)

    @patch("pyplumio.parameters.Switch.set_nowait")
    async def test_switch_turn_off_nowait(
        self, mock_set_nowait, switch: Switch
    ) -> None:
        """Test turn_off_nowait.

        Checks turning switch off without waiting.
        """
        switch.turn_off_nowait()
        mock_set_nowait.assert_called_once_with(STATE_OFF)

    @pytest.mark.parametrize(
        ("state", "expected_result"),
        [(STATE_ON, True), (STATE_OFF, False), (True, True), (False, False)],
    )
    def test_states(
        self,
        state: State | bool,
        expected_result: bool,
        switch: Switch,
    ) -> None:
        """Test states.

        Checks switch equality using integers and states.
        """
        switch.update(ParameterValues(1, 0, 1))
        assert switch.__eq__(state) is expected_result
