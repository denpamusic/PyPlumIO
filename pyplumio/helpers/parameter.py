"""Contains a device parameter class."""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from dataclasses import dataclass
import logging
from typing import TYPE_CHECKING, Any, Literal, TypeVar, Union

from dataslots import dataslots
from typing_extensions import TypeAlias

from pyplumio.const import BYTE_UNDEFINED, STATE_OFF, STATE_ON, UnitOfMeasurement
from pyplumio.frames import Request

if TYPE_CHECKING:
    from pyplumio.devices import Device

_LOGGER = logging.getLogger(__name__)


ParameterValue: TypeAlias = Union[int, float, bool, Literal["off", "on"]]
ParameterT = TypeVar("ParameterT", bound="Parameter")


def unpack_parameter(
    data: bytearray, offset: int = 0, size: int = 1
) -> ParameterValues | None:
    """Unpack a device parameter."""
    if not check_parameter(data[offset : offset + size * 3]):
        return None

    value = data[offset : offset + size]
    min_value = data[offset + size : offset + 2 * size]
    max_value = data[offset + 2 * size : offset + 3 * size]

    return ParameterValues(
        value=int.from_bytes(value, byteorder="little"),
        min_value=int.from_bytes(min_value, byteorder="little"),
        max_value=int.from_bytes(max_value, byteorder="little"),
    )


def check_parameter(data: bytearray) -> bool:
    """Check if parameter contains any bytes besides 0xFF."""
    return any(x for x in data if x != BYTE_UNDEFINED)


def _normalize_parameter_value(value: ParameterValue) -> int:
    """Normalize a parameter value."""
    if value in (STATE_OFF, STATE_ON):
        return 1 if value == STATE_ON else 0

    return int(value)


@dataclass
class ParameterValues:
    """Represents a parameter values."""

    __slots__ = ("value", "min_value", "max_value")

    value: int
    min_value: int
    max_value: int


@dataslots
@dataclass
class ParameterDescription:
    """Represents a parameter description."""

    name: str


class Parameter(ABC):
    """Represents a base parameter."""

    __slots__ = (
        "device",
        "description",
        "_pending_update",
        "_previous_value",
        "_index",
        "_values",
    )

    device: Device
    description: ParameterDescription
    _pending_update: bool
    _previous_value: int
    _index: int
    _values: ParameterValues

    def __init__(
        self,
        device: Device,
        description: ParameterDescription,
        values: ParameterValues | None = None,
        index: int = 0,
    ):
        """Initialize a new parameter."""
        self.device = device
        self.description = description
        self._pending_update = False
        self._previous_value = 0
        self._index = index
        self._values = values if values else ParameterValues(0, 0, 0)

    def __repr__(self) -> str:
        """Return a serializable string representation."""
        return (
            f"{self.__class__.__name__}("
            f"device={self.device.__class__.__name__}, "
            f"description={self.description}, "
            f"values={self.values}, "
            f"index={self._index})"
        )

    def _call_relational_method(self, method_to_call: str, other: Any) -> Any:
        """Call a specified relational method."""
        if isinstance(other, Parameter):
            other = other.values

        if isinstance(other, ParameterValues):
            handler = getattr(self.values, method_to_call)
            return handler(other)

        if isinstance(other, (int, float, bool)) or other in (STATE_OFF, STATE_ON):
            handler = getattr(self.values.value, method_to_call)
            return handler(_normalize_parameter_value(other))
        else:
            return NotImplemented

    def __int__(self) -> int:
        """Return an integer representation of parameter's value."""
        return self.values.value

    def __add__(self, other: Any) -> Any:
        """Return result of addition."""
        return self._call_relational_method("__add__", other)

    def __sub__(self, other: Any) -> Any:
        """Return result of the subtraction."""
        return self._call_relational_method("__sub__", other)

    def __truediv__(self, other: Any) -> Any:
        """Return result of true division."""
        return self._call_relational_method("__truediv__", other)

    def __floordiv__(self, other: Any) -> Any:
        """Return result of floored division."""
        return self._call_relational_method("__floordiv__", other)

    def __mul__(self, other: Any) -> Any:
        """Return result of the multiplication."""
        return self._call_relational_method("__mul__", other)

    def __eq__(self, other: Any) -> Any:
        """Compare if parameter value is equal to other."""
        return self._call_relational_method("__eq__", other)

    def __ge__(self, other: Any) -> Any:
        """Compare if parameter value is greater or equal to other."""
        return self._call_relational_method("__ge__", other)

    def __gt__(self, other: Any) -> Any:
        """Compare if parameter value is greater than other."""
        return self._call_relational_method("__gt__", other)

    def __le__(self, other: Any) -> Any:
        """Compare if parameter value is less or equal to other."""
        return self._call_relational_method("__le__", other)

    def __lt__(self, other: Any) -> Any:
        """Compare if parameter value is less that other."""
        return self._call_relational_method("__lt__", other)

    def __copy__(self) -> Parameter:
        """Create a copy of parameter."""
        values = type(self.values)(
            self.values.value, self.values.min_value, self.values.max_value
        )
        return type(self)(self.device, self.description, values)

    async def set(self, value: Any, retries: int = 5, timeout: float = 5.0) -> bool:
        """Set a parameter value."""
        if (value := _normalize_parameter_value(value)) == self.values.value:
            return True

        if value < self.values.min_value or value > self.values.max_value:
            raise ValueError(
                f"Value must be between '{self.min_value}' and '{self.max_value}'"
            )

        self._previous_value = self._values.value
        self._values.value = value
        self._pending_update = True
        while self.pending_update:
            if retries <= 0:
                _LOGGER.error(
                    "Timed out while trying to set '%s' parameter",
                    self.description.name,
                )
                return False

            await self.device.queue.put(await self.create_request())
            if not self.is_tracking_changes:
                await self.force_refresh()

            await asyncio.sleep(timeout)
            retries -= 1

        return True

    def update(self, values: ParameterValues) -> None:
        """Update the parameter values."""
        if self.pending_update and self._previous_value != values.value:
            self._pending_update = False

        self._values = values

    async def force_refresh(self) -> None:
        """Refresh the parameter from remote."""
        await self.device.queue.put(await self.create_refresh_request())

    @property
    def is_tracking_changes(self) -> bool:
        """Return True if remote's tracking changes, False otherwise."""
        return False

    @property
    def pending_update(self) -> bool:
        """Check if parameter is pending update on the device."""
        return self._pending_update

    @property
    def values(self) -> ParameterValues:
        """Return the parameter values."""
        return self._values

    @classmethod
    def create_or_update(
        cls: type[ParameterT],
        device: Device,
        description: ParameterDescription,
        values: ParameterValues,
        **kwargs: Any,
    ) -> ParameterT:
        """Create new parameter or update parameter values."""
        parameter: ParameterT | None = device.get_nowait(description.name, None)
        if parameter and isinstance(parameter, cls):
            parameter.update(values)
        else:
            parameter = cls(
                device=device, description=description, values=values, **kwargs
            )

        return parameter

    @property
    @abstractmethod
    def value(self) -> Any:
        """Return the value."""

    @property
    @abstractmethod
    def min_value(self) -> Any:
        """Return the minimum allowed value."""

    @property
    @abstractmethod
    def max_value(self) -> Any:
        """Return the maximum allowed value."""

    @abstractmethod
    async def create_request(self) -> Request:
        """Create a request to change the parameter."""

    @abstractmethod
    async def create_refresh_request(self) -> Request:
        """Create a request to refresh the parameter."""


@dataslots
@dataclass
class NumberDescription(ParameterDescription):
    """Represents a parameter description."""

    unit_of_measurement: UnitOfMeasurement | Literal["%"] | None = None


class Number(Parameter):
    """Represents a number."""

    __slots__ = ()

    description: NumberDescription

    async def set(
        self, value: int | float, retries: int = 5, timeout: float = 5.0
    ) -> bool:
        """Set a parameter value."""
        return await super().set(value, retries, timeout)

    def set_nowait(
        self, value: int | float, retries: int = 5, timeout: float = 5.0
    ) -> None:
        """Set a parameter value without waiting."""
        self.device.create_task(self.set(value, retries, timeout))

    async def create_request(self) -> Request:
        """Create a request to change the number."""
        return Request()

    async def create_refresh_request(self) -> Request:
        """Create a request to refresh the number."""
        return Request()

    @property
    def value(self) -> int | float:
        """Return the value."""
        return self.values.value

    @property
    def min_value(self) -> int | float:
        """Return the minimum allowed value."""
        return self.values.min_value

    @property
    def max_value(self) -> int | float:
        """Return the maximum allowed value."""
        return self.values.max_value

    @property
    def unit_of_measurement(self) -> UnitOfMeasurement | Literal["%"] | None:
        """Return the unit of measurement."""
        return self.description.unit_of_measurement


@dataslots
@dataclass
class SwitchDescription(ParameterDescription):
    """Represents a switch description."""


class Switch(Parameter):
    """Represents a switch."""

    __slots__ = ()

    description: SwitchDescription

    async def set(
        self, value: bool | Literal["off", "on"], retries: int = 5, timeout: float = 5.0
    ) -> bool:
        """Set a parameter value."""
        return await super().set(value, retries, timeout)

    def set_nowait(
        self, value: bool | Literal["off", "on"], retries: int = 5, timeout: float = 5.0
    ) -> None:
        """Set a switch value without waiting."""
        self.device.create_task(self.set(value, retries, timeout))

    async def turn_on(self) -> bool:
        """Set a switch value to 'on'.

        :return: `True` if parameter was successfully turned on, `False`
            otherwise.
        :rtype: bool
        """
        return await self.set(STATE_ON)

    async def turn_off(self) -> bool:
        """Set a switch value to 'off'.

        :return: `True` if parameter was successfully turned off, `False`
            otherwise.
        :rtype: bool
        """
        return await self.set(STATE_OFF)

    def turn_on_nowait(self) -> None:
        """Set a switch value to 'on' without waiting."""
        self.set_nowait(STATE_ON)

    def turn_off_nowait(self) -> None:
        """Set a switch value to 'off' without waiting."""
        self.set_nowait(STATE_OFF)

    async def create_request(self) -> Request:
        """Create a request to change the switch."""
        return Request()

    async def create_refresh_request(self) -> Request:
        """Create a request to refresh the switch."""
        return Request()

    @property
    def value(self) -> Literal["off", "on"]:
        """Return the value."""
        return STATE_ON if self.values.value == 1 else STATE_OFF

    @property
    def min_value(self) -> Literal["off"]:
        """Return the minimum allowed value."""
        return STATE_OFF

    @property
    def max_value(self) -> Literal["on"]:
        """Return the maximum allowed value."""
        return STATE_ON
