"""Contains device parameter representation."""
from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from typing import Any, Final

from pyplumio.const import ATTR_EXTRA, ATTR_NAME, ATTR_VALUE
from pyplumio.frames import Request
from pyplumio.helpers.factory import factory
from pyplumio.helpers.typing import ParameterDataType, ParameterValueType

STATE_ON: Final = "on"
STATE_OFF: Final = "off"


def _normalize_parameter_value(value: ParameterValueType) -> int:
    """Normalize parameter value to integer."""
    if isinstance(value, str):
        return 1 if value == STATE_ON else 0

    if isinstance(value, tuple):
        # Value is parameter tuple.
        value = value[0]

    return int(value)


def is_binary_parameter(parameter: ParameterDataType) -> bool:
    """Check if parameter is binary."""
    _, min_value, max_value = parameter
    return min_value == 0 and max_value == 1


class Parameter(ABC):
    """Represents device parameter."""

    name: str
    extra: Any
    _value: int
    _min_value: int
    _max_value: int
    _changed: bool = False

    def __init__(
        self,
        queue: asyncio.Queue,
        recipient: int,
        name: str,
        value: ParameterValueType,
        min_value: ParameterValueType,
        max_value: ParameterValueType,
        extra: Any = None,
    ):
        """Initialize Parameter object."""
        self.recipient = recipient
        self.name = name
        self.extra = extra
        self._queue = queue
        self._value = _normalize_parameter_value(value)
        self._min_value = _normalize_parameter_value(min_value)
        self._max_value = _normalize_parameter_value(max_value)
        self._changed = False

    def __repr__(self) -> str:
        """Returns serializable string representation."""
        return f"""{self.__class__.__name__}(
    queue = asyncio.Queue(),
    recipient = {self.recipient},
    name = {self.name},
    value = {self._value},
    min_value = {self._min_value},
    max_value = {self._max_value},
    extra = {self.extra}
)"""

    def _call_relational_method(self, method_to_call, other):
        func = getattr(self.value, method_to_call)
        return func(_normalize_parameter_value(other))

    def __int__(self) -> int:
        """Return integer representation of parameter value."""
        return self.value

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

    def set(self, value: ParameterValueType) -> None:
        """Set parameter value."""
        value = _normalize_parameter_value(value)
        if value == self._value:
            return

        if self.min_value <= value <= self.max_value:
            self._value = value
            self._queue.put_nowait(self.request)
            self._changed = True
        else:
            raise ValueError(
                f"Parameter value must be between {self.min_value} and {self.max_value}"
            )

    @property
    def value(self) -> int:
        """Return parameter value."""
        return self._value

    @property
    def min_value(self) -> int:
        """Return minimum allowed value."""
        return self._min_value

    @property
    def max_value(self) -> int:
        """Return maximum allowed value."""
        return self._max_value

    @property
    def changed(self) -> bool:
        """Has parameter been changed recently."""
        return self._changed

    @property
    @abstractmethod
    def request(self) -> Request:
        """Return request to change the parameter."""


class BinaryParameter(Parameter):
    """Represents binary device parameter."""

    def turn_on(self) -> None:
        """Turn parameter on."""
        self.set(STATE_ON)

    def turn_off(self) -> None:
        """Turn parameter off"""
        self.set(STATE_OFF)


class BoilerParameter(Parameter):
    """Represents boiler parameter."""

    @property
    def request(self) -> Request:
        """Return request to change the parameter."""
        handler = (
            "frames.requests.BoilerControlRequest"
            if self.name == "boiler_control"
            else "frames.requests.SetBoilerParameterRequest"
        )

        return factory(
            handler,
            recipient=self.recipient,
            data={ATTR_NAME: self.name, ATTR_VALUE: self.value},
        )


class BoilerBinaryParameter(BoilerParameter, BinaryParameter):
    """Represents boiler binary parameter."""


class MixerParameter(Parameter):
    """Represents mixer parameter."""

    @property
    def request(self) -> Request:
        """Return request to change the parameter."""
        return factory(
            "frames.requests.SetMixerParameterRequest",
            recipient=self.recipient,
            data={ATTR_NAME: self.name, ATTR_VALUE: self.value, ATTR_EXTRA: self.extra},
        )


class MixerBinaryParameter(MixerParameter, BinaryParameter):
    """Represents mixer binary parameter."""
