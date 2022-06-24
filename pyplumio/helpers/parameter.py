"""Contains device parameter representation."""
from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from typing import Any, Union

from pyplumio.frames import Request
from pyplumio.helpers.classname import ClassName
from pyplumio.helpers.factory import factory
from pyplumio.typing import Numeric


class Parameter(ABC, ClassName):
    """Represents device parameter."""

    name: str
    value: int
    min_value: int
    max_value: int
    extra: Any

    def __init__(
        self,
        queue: asyncio.Queue,
        recipient: int,
        name: str,
        value: Numeric,
        min_value: Numeric,
        max_value: Numeric,
        extra: Any = None,
    ):
        """Initialize Parameter object."""
        self.recipient = recipient
        self.name = name
        self.value = int(value)
        self.min_value = int(min_value)
        self.max_value = int(max_value)
        self.extra = extra
        self._queue = queue

    def __repr__(self) -> str:
        """Returns serializable string representation."""
        return f"""{self.get_classname()}(
    queue = asyncio.Queue(),
    recipient = {self.recipient},
    name = {self.name},
    value = {self.value},
    min_value = {self.min_value},
    max_value = {self.max_value},
    extra = {self.extra}
)"""

    def __int__(self) -> int:
        """Return integer representation of parameter value."""
        return int(self.value)

    def __eq__(self, other) -> bool:
        """Compare if parameter value is equal to other."""
        return self.value == other

    def __ge__(self, other) -> int:
        """Compare if parameter value is greater or equal to other."""
        return self.value >= other

    def __gt__(self, other) -> int:
        """Compare if parameter value is greater than other."""
        return self.value > other

    def __le__(self, other) -> int:
        """Compare if parameter value is less or equal to other."""
        return self.value <= other

    def __lt__(self, other) -> int:
        """Compare if parameter value is less that other."""
        return self.value < other

    def set(self, value: Union[int, float]) -> None:
        """Set parameter value."""
        value = int(value)
        if self.value != value and self.min_value <= value <= self.max_value:
            self.value = value
            self._queue.put_nowait(self.request)
        else:
            raise ValueError(
                f"parameter value must be between {self.min_value} and {self.max_value}"
            )

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

        return factory(handler, recipient=self.recipient, data=self.__dict__)


class MixerParameter(Parameter):
    """Represents mixer parameter."""

    @property
    def request(self) -> Request:
        """Return request to change the parameter."""
        return factory(
            "frames.requests.SetMixerParameter",
            recipient=self.recipient,
            data=self.__dict__,
        )
