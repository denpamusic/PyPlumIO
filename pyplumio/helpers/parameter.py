"""Contains a device parameter class."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging
from typing import TYPE_CHECKING, Final

from pyplumio.const import STATE_OFF, STATE_ON
from pyplumio.frames import Request
from pyplumio.helpers.typing import ParameterValueType

if TYPE_CHECKING:
    from pyplumio.devices import Device

_LOGGER = logging.getLogger(__name__)

SET_TIMEOUT: Final = 5
SET_RETRIES: Final = 5


def _normalize_parameter_value(value: ParameterValueType) -> int:
    """Normalize a parameter value to an integer."""
    if isinstance(value, str):
        return 1 if value == STATE_ON else 0

    if isinstance(value, tuple):
        # Value is parameter tuple.
        value = value[0]

    return int(value)


@dataclass
class ParameterDescription:
    """Represents a parameter description."""

    name: str


class Parameter:
    """Represents a parameter."""

    device: Device
    description: ParameterDescription
    _value: int
    _min_value: int
    _max_value: int
    _is_changed: bool = False
    _index: int

    def __init__(
        self,
        device: Device,
        value: ParameterValueType,
        min_value: ParameterValueType,
        max_value: ParameterValueType,
        description: ParameterDescription,
        index: int = 0,
    ):
        """Initialize a new parameter."""
        self.index = index
        self.device = device
        self.description = description
        self._value = _normalize_parameter_value(value)
        self._min_value = _normalize_parameter_value(min_value)
        self._max_value = _normalize_parameter_value(max_value)
        self._is_changed = False
        self._index = index

    def __repr__(self) -> str:
        """Return a serializable string representation."""
        return (
            self.__class__.__name__
            + f"(device={self.device.__class__.__name__}, "
            + f"description={self.description}, value={self.value}, "
            + f"min_value={self.min_value}, max_value={self.max_value})"
        )

    def _call_relational_method(self, method_to_call, other):
        """Call a specified relational method."""
        func = getattr(self._value, method_to_call)
        return func(_normalize_parameter_value(other))

    def __int__(self) -> int:
        """Return an integer representation of parameter's value."""
        return self._value

    def __add__(self, other) -> int:
        """Return result of addition."""
        return self._call_relational_method("__add__", other)

    def __sub__(self, other) -> int:
        """Return result of the subtraction."""
        return self._call_relational_method("__sub__", other)

    def __truediv__(self, other):
        """Return result of true division."""
        return self._call_relational_method("__truediv__", other)

    def __floordiv__(self, other):
        """Return result of floored division."""
        return self._call_relational_method("__floordiv__", other)

    def __mul__(self, other):
        """Return result of the multiplication."""
        return self._call_relational_method("__mul__", other)

    def __eq__(self, other) -> bool:
        """Compare if parameter value is equal to other."""
        return self._call_relational_method("__eq__", other)

    def __ge__(self, other) -> bool:
        """Compare if parameter value is greater or equal to other."""
        return self._call_relational_method("__ge__", other)

    def __gt__(self, other) -> bool:
        """Compare if parameter value is greater than other."""
        return self._call_relational_method("__gt__", other)

    def __le__(self, other) -> bool:
        """Compare if parameter value is less or equal to other."""
        return self._call_relational_method("__le__", other)

    def __lt__(self, other) -> bool:
        """Compare if parameter value is less that other."""
        return self._call_relational_method("__lt__", other)

    async def _confirm_parameter_change(self, parameter: Parameter) -> None:
        """A callback for when parameter change is confirmed on
        the device.
        """
        self._is_changed = False

    async def set(self, value: ParameterValueType, retries: int = SET_RETRIES) -> bool:
        """Set a parameter value."""
        if (value := _normalize_parameter_value(value)) == self._value:
            return True

        if value < self._min_value or value > self._max_value:
            raise ValueError(
                f"Parameter value must be between '{self.min_value}' and '{self.max_value}'"
            )

        self._value = value
        self._is_changed = True
        self.device.subscribe_once(
            self.description.name, self._confirm_parameter_change
        )
        while self.is_changed:
            if retries <= 0:
                _LOGGER.error(
                    "Timed out while trying to set '%s' parameter",
                    self.description.name,
                )
                self.device.unsubscribe(
                    self.description.name, self._confirm_parameter_change
                )
                return False

            await self.device.queue.put(self.request)
            await asyncio.sleep(SET_TIMEOUT)
            retries -= 1

        return True

    def set_nowait(self, value: ParameterValueType, retries: int = SET_RETRIES) -> None:
        """Set a parameter value without waiting."""
        self.device.create_task(self.set(value, retries))

    @property
    def is_changed(self) -> bool:
        """Check if parameter change is confirmed on the device."""
        return self._is_changed

    @property
    def value(self) -> ParameterValueType:
        """A parameter value."""
        return self._value

    @property
    def min_value(self) -> ParameterValueType:
        """Minimum allowed value."""
        return self._min_value

    @property
    def max_value(self) -> ParameterValueType:
        """Maximum allowed value."""
        return self._max_value

    @property
    def request(self) -> Request:
        """A request to change the parameter."""
        raise NotImplementedError


class BinaryParameter(Parameter):
    """Represents binary device parameter."""

    async def turn_on(self) -> bool:
        """Set a parameter value to 'on'."""
        return await self.set(STATE_ON)

    async def turn_off(self) -> bool:
        """Set a parameter value to 'off'."""
        return await self.set(STATE_OFF)

    def turn_on_nowait(self) -> None:
        """Set a parameter state to 'on' without waiting."""
        self.set_nowait(STATE_ON)

    def turn_off_nowait(self) -> None:
        """Set a parameter state to 'off' without waiting."""
        self.set_nowait(STATE_OFF)

    @property
    def value(self) -> ParameterValueType:
        """A parameter value."""
        return STATE_ON if self._value == 1 else STATE_OFF

    @property
    def min_value(self) -> ParameterValueType:
        """Minimum allowed value."""
        return STATE_OFF

    @property
    def max_value(self) -> ParameterValueType:
        """Maximum allowed value."""
        return STATE_ON
