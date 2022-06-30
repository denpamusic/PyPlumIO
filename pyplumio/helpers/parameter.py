"""Contains device parameter representation."""
from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from typing import Any

from pyplumio.const import STATE_OFF, STATE_ON
from pyplumio.frames import Request
from pyplumio.helpers.factory import factory
from pyplumio.typing import ParameterTuple, ParameterValue


def _normalize_parameter_value(value: ParameterValue) -> int:
    """Normalize parameter value to integer."""
    if isinstance(value, str):
        return 1 if value == STATE_ON else 0

    return int(value)


def is_binary_parameter(parameter: ParameterTuple) -> bool:
    """Check if parameter is binary."""
    _, _, min_value, max_value = parameter
    return min_value == 0 and max_value == 1


class Parameter(ABC):
    """Represents device parameter."""

    name: str
    extra: Any
    _value: int
    _min_value: int
    _max_value: int

    def __init__(
        self,
        queue: asyncio.Queue,
        recipient: int,
        name: str,
        value: ParameterValue,
        min_value: ParameterValue,
        max_value: ParameterValue,
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

    def __int__(self) -> int:
        """Return integer representation of parameter value."""
        return self.value

    def __eq__(self, other) -> bool:
        """Compare if parameter value is equal to other."""
        return self.value == _normalize_parameter_value(other)

    def __ge__(self, other) -> int:
        """Compare if parameter value is greater or equal to other."""
        return self.value >= _normalize_parameter_value(other)

    def __gt__(self, other) -> int:
        """Compare if parameter value is greater than other."""
        return self.value > _normalize_parameter_value(other)

    def __le__(self, other) -> int:
        """Compare if parameter value is less or equal to other."""
        return self.value <= _normalize_parameter_value(other)

    def __lt__(self, other) -> int:
        """Compare if parameter value is less that other."""
        return self.value < _normalize_parameter_value(other)

    def set(self, value: ParameterValue) -> None:
        """Set parameter value."""
        value = _normalize_parameter_value(value)
        if value == self._value:
            return

        if self.min_value <= value <= self.max_value:
            self._value = value
            self._queue.put_nowait(self.request)
        else:
            raise ValueError(
                f"parameter value must be between {self.min_value} and {self.max_value}"
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
            "frames.requests.BoilerControl"
            if self.name == "boiler_control"
            else "frames.requests.SetBoilerParameter"
        )

        return factory(
            handler,
            recipient=self.recipient,
            data={"name": self.name, "value": self.value},
        )


class BoilerBinaryParameter(BoilerParameter, BinaryParameter):
    """Represents boiler binary parameter."""


class MixerParameter(Parameter):
    """Represents mixer parameter."""

    @property
    def request(self) -> Request:
        """Return request to change the parameter."""
        return factory(
            "frames.requests.SetMixerParameter",
            recipient=self.recipient,
            data={"name": self.name, "value": self.value, "extra": self.extra},
        )


class MixerBinaryParameter(MixerParameter, BinaryParameter):
    """Represents mixer binary parameter."""
