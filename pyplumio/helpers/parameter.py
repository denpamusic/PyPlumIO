"""Contains device parameter representation."""
from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from typing import Any

from pyplumio.const import STATE_ON
from pyplumio.frames import Request
from pyplumio.helpers.classname import ClassName
from pyplumio.helpers.factory import factory
from pyplumio.typing import ParameterValue


def _normalize_parameter_value(value: ParameterValue) -> int:
    """Normalize parameter value to integer."""
    if isinstance(value, str):
        return 1 if value == STATE_ON else 0

    return int(value)


class Parameter(ABC, ClassName):
    """Represents device parameter."""

    name: str
    extra: Any
    _value: ParameterValue
    _min_value: ParameterValue
    _max_value: ParameterValue

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
        self._value = value
        self._min_value = min_value
        self._max_value = max_value

    def __repr__(self) -> str:
        """Returns serializable string representation."""
        return f"""{self.get_classname()}(
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
        return _normalize_parameter_value(self.value)

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
        if value == self.value:
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
        return _normalize_parameter_value(self._value)

    @property
    def min_value(self) -> int:
        """Return minimum allowed value."""
        return _normalize_parameter_value(self._min_value)

    @property
    def max_value(self) -> int:
        """Return maximum allowed value."""
        return _normalize_parameter_value(self._max_value)

    @property
    @abstractmethod
    def request(self) -> Request:
        """Return request to change the parameter."""


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
