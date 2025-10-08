"""Contains a device parameter class."""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from contextlib import suppress
from dataclasses import asdict, dataclass
import logging
from typing import TYPE_CHECKING, Any, Literal, TypeAlias, TypeVar, get_args

from pyplumio.const import BYTE_UNDEFINED, STATE_OFF, STATE_ON, State, UnitOfMeasurement
from pyplumio.frames import Request
from pyplumio.utils import is_divisible

if TYPE_CHECKING:
    from pyplumio.devices import Device

_LOGGER = logging.getLogger(__name__)

_ParameterT = TypeVar("_ParameterT", bound="Parameter")


def unpack_parameter(
    data: bytearray, offset: int = 0, size: int = 1
) -> ParameterValues | None:
    """Unpack a device parameter."""
    if not is_valid_parameter(data[offset : offset + size * 3]):
        return None

    value = data[offset : offset + size]
    min_value = data[offset + size : offset + 2 * size]
    max_value = data[offset + 2 * size : offset + 3 * size]

    return ParameterValues(
        value=int.from_bytes(value, byteorder="little"),
        min_value=int.from_bytes(min_value, byteorder="little"),
        max_value=int.from_bytes(max_value, byteorder="little"),
    )


def is_valid_parameter(data: bytearray) -> bool:
    """Check if parameter contains any bytes besides 0xFF."""
    return any(x for x in data if x != BYTE_UNDEFINED)


@dataclass(slots=True)
class ParameterValues:
    """Represents a parameter values."""

    value: int
    min_value: int
    max_value: int


@dataclass(slots=True)
class ParameterDescription:
    """Represents a parameter description."""

    name: str
    optimistic: bool = False


Numeric: TypeAlias = int | float


class Parameter(ABC):
    """Represents a base parameter."""

    __slots__ = (
        "device",
        "description",
        "_update_done",
        "_update_pending",
        "_index",
        "_values",
    )

    device: Device
    description: ParameterDescription
    _update_done: asyncio.Event
    _update_pending: asyncio.Event
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
        self._index = index
        self._index = index
        self._update_done = asyncio.Event()
        self._update_pending = asyncio.Event()
        self._values = values if values else ParameterValues(0, 0, 0)

    def __repr__(self) -> str:
        """Return a serializable string representation."""
        return (
            f"{self.__class__.__name__}("
            f"device={self.device}, "
            f"description={self.description}, "
            f"values={self.values}, "
            f"index={self._index})"
        )

    def __hash__(self) -> int:
        """Return a hash of the parameter based on its values."""
        return hash(frozenset(asdict(self.values).items()))

    def _call_relational_method(self, method_to_call: str, other: Any) -> Any:
        """Call a specified relational method."""
        handler = getattr(self.values.value, method_to_call)
        if isinstance(other, Parameter):
            return handler(other.values.value)

        if isinstance(other, ParameterValues):
            return handler(other.value)

        if isinstance(other, Numeric | bool) or other in get_args(State):
            return handler(self._pack_value(other))

        return NotImplemented

    def __int__(self) -> int:
        """Return an integer representation of parameter's value."""
        return self.values.value

    def __add__(self, other: Any) -> Any:
        """Add a number to this parameter."""
        return self._call_relational_method("__add__", other)

    def __radd__(self, other: Any) -> Any:
        """Add this parameter to another number."""
        return self._call_relational_method("__radd__", other)

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

    async def set(self, value: Any, retries: int = 0, timeout: float = 5.0) -> bool:
        """Set a parameter value."""
        self.validate(value)
        return await self._attempt_update(self._pack_value(value), retries, timeout)

    def set_nowait(self, value: Any, retries: int = 0, timeout: float = 5.0) -> None:
        """Set a parameter value without waiting."""
        self.validate(value)
        self.device.create_task(
            self._attempt_update(self._pack_value(value), retries, timeout)
        )

    async def _attempt_update(self, value: int, retries: int, timeout: float) -> bool:
        """Attempt to update a parameter value on the remote device."""
        _LOGGER.info(
            "Attempting to update '%s' parameter to %d", self.description.name, value
        )
        if value == self.values.value:
            # Value is unchanged
            return True

        self._values.value = value
        request = await self.create_request()
        if self.description.optimistic:
            await self.device.queue.put(request)
            return True

        self.update_done.clear()
        self.update_pending.set()
        if retries > 0:
            return await self._attempt_update_with_retries(
                request, retries=retries, timeout=timeout
            )

        return await self._send_update_request(request, timeout=timeout)

    async def _attempt_update_with_retries(
        self, request: Request, retries: int, timeout: float
    ) -> bool:
        """Send update request and retry until success."""
        for _ in range(retries):
            if await self._send_update_request(request, timeout=timeout):
                return True

        _LOGGER.warning(
            "Unable to confirm update of '%s' parameter after %d retries",
            self.description.name,
            retries,
        )
        return False

    async def _send_update_request(self, request: Request, timeout: float) -> bool:
        """Send update request to the remote and confirm the result."""
        await self.device.queue.put(request)
        with suppress(asyncio.TimeoutError):
            # Wait for the update to be done
            await asyncio.wait_for(self.update_done.wait(), timeout=timeout)

        return self.update_done.is_set()

    def update(self, values: ParameterValues) -> None:
        """Update the parameter values."""
        self.update_done.set()
        self.update_pending.clear()
        self._values = values

    @property
    def update_done(self) -> asyncio.Event:
        """Check if parameter is updated on the device."""
        return self._update_done

    @property
    def update_pending(self) -> asyncio.Event:
        """Check if parameter is updated on the device."""
        return self._update_pending

    @property
    def values(self) -> ParameterValues:
        """Return the parameter values."""
        return self._values

    @classmethod
    def create_or_update(
        cls: type[_ParameterT],
        device: Device,
        description: ParameterDescription,
        values: ParameterValues,
        **kwargs: Any,
    ) -> _ParameterT:
        """Create new parameter or update parameter values."""
        parameter: _ParameterT | None = device.get_nowait(description.name, None)
        if parameter and isinstance(parameter, cls):
            parameter.update(values)
        else:
            parameter = cls(
                device=device, description=description, values=values, **kwargs
            )

        return parameter

    @abstractmethod
    def _pack_value(self, value: Any) -> int:
        """Pack the parameter value."""

    @abstractmethod
    def _unpack_value(self, value: int) -> Any:
        """Unpack the parameter value."""

    @abstractmethod
    def validate(self, value: Any) -> bool:
        """Validate a parameter value."""

    @property
    @abstractmethod
    def value(self) -> Numeric | State | bool:
        """Return the value."""

    @property
    @abstractmethod
    def min_value(self) -> Numeric | State | bool:
        """Return the minimum allowed value."""

    @property
    @abstractmethod
    def max_value(self) -> Numeric | State | bool:
        """Return the maximum allowed value."""

    @abstractmethod
    async def create_request(self) -> Request:
        """Create a request to change the parameter."""


@dataclass(slots=True)
class NumberDescription(ParameterDescription):
    """Represents a parameter description."""

    step: float = 1.0
    precision: int = 6
    unit_of_measurement: UnitOfMeasurement | Literal["%"] | None = None


class Number(Parameter):
    """Represents a number."""

    __slots__ = ()

    description: NumberDescription

    def __float__(self) -> float:
        """Return number value as float."""
        return float(self.value)

    def _pack_value(self, value: Numeric) -> int:
        """Pack the parameter value."""
        return int(round(value / self.description.step))

    def _unpack_value(self, value: int) -> Numeric:
        """Unpack the parameter value."""
        return round(value * self.description.step, self.description.precision)

    def validate(self, value: Any) -> bool:
        """Validate a parameter value."""
        if value < self.min_value or value > self.max_value:
            raise ValueError(
                f"Invalid value: {value}. The value must be between {self.min_value} "
                f"and {self.max_value}."
            )

        if not is_divisible(value, self.description.step, self.description.precision):
            raise ValueError(
                f"Invalid value: {value}. The value must be adjusted in increments of "
                f"{self.description.step}."
            )

        return True

    async def set(self, value: Numeric, retries: int = 0, timeout: float = 5.0) -> bool:
        """Set a parameter value."""
        return await super().set(value, retries=retries, timeout=timeout)

    def set_nowait(
        self, value: Numeric, retries: int = 0, timeout: float = 5.0
    ) -> None:
        """Set a parameter value without waiting."""
        super().set_nowait(value, retries=retries, timeout=timeout)

    async def create_request(self) -> Request:
        """Create a request to change the number."""
        return Request()

    @property
    def value(self) -> Numeric:
        """Return the value."""
        return self._unpack_value(self.values.value)

    @property
    def min_value(self) -> Numeric:
        """Return the minimum allowed value."""
        return self._unpack_value(self.values.min_value)

    @property
    def max_value(self) -> Numeric:
        """Return the maximum allowed value."""
        return self._unpack_value(self.values.max_value)

    @property
    def unit_of_measurement(self) -> UnitOfMeasurement | Literal["%"] | None:
        """Return the unit of measurement."""
        return self.description.unit_of_measurement


@dataclass(slots=True)
class OffsetNumberDescription(NumberDescription):
    """Represents a parameter description."""

    offset: int = 0


class OffsetNumber(Number):
    """Represents a number with offset."""

    __slots__ = ()

    description: OffsetNumberDescription

    def _pack_value(self, value: Numeric) -> int:
        """Pack the parameter value."""
        return super()._pack_value(value + self.description.offset)

    def _unpack_value(self, value: int) -> Numeric:
        """Unpack the parameter value."""
        return super()._unpack_value(value - self.description.offset)


@dataclass(slots=True)
class SwitchDescription(ParameterDescription):
    """Represents a switch description."""


class Switch(Parameter):
    """Represents a switch."""

    __slots__ = ()

    description: SwitchDescription

    def _pack_value(self, value: State | bool) -> int:
        """Pack the parameter value."""
        if value in get_args(State):
            return 1 if value == STATE_ON else 0

        return int(value)

    def _unpack_value(self, value: int) -> State:
        """Unpack the parameter value."""
        return STATE_ON if value == 1 else STATE_OFF

    def validate(self, value: Any) -> bool:
        """Validate a parameter value."""
        if not isinstance(value, bool) and value not in get_args(State):
            raise ValueError(
                f"Invalid value: {value}. The value must be either 'on', 'off' or "
                f"boolean."
            )

        return True

    async def set(
        self, value: State | bool, retries: int = 0, timeout: float = 5.0
    ) -> bool:
        """Set a parameter value."""
        return await super().set(value, retries=retries, timeout=timeout)

    def set_nowait(
        self, value: State | bool, retries: int = 0, timeout: float = 5.0
    ) -> None:
        """Set a switch value without waiting."""
        super().set_nowait(value, retries=retries, timeout=timeout)

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

    @property
    def value(self) -> State:
        """Return the value."""
        return self._unpack_value(self.values.value)

    @property
    def min_value(self) -> Literal["off"]:
        """Return the minimum allowed value."""
        return STATE_OFF

    @property
    def max_value(self) -> Literal["on"]:
        """Return the maximum allowed value."""
        return STATE_ON


__all__ = [
    "Number",
    "NumberDescription",
    "Numeric",
    "OffsetNumber",
    "OffsetNumberDescription",
    "Parameter",
    "ParameterDescription",
    "ParameterValues",
    "State",
    "Switch",
    "SwitchDescription",
]
