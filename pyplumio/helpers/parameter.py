"""Contains a device parameter class."""
from __future__ import annotations

from abc import ABC
import asyncio
from dataclasses import dataclass
import logging
from typing import TYPE_CHECKING, Final, Literal

from pyplumio.const import BYTE_UNDEFINED, STATE_OFF, STATE_ON, UnitOfMeasurement
from pyplumio.frames import Request
from pyplumio.helpers.typing import ParameterValueType

if TYPE_CHECKING:
    from pyplumio.devices import Device

_LOGGER = logging.getLogger(__name__)

SET_TIMEOUT: Final = 5
SET_RETRIES: Final = 5


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


def _normalize_parameter_value(value: ParameterValueType) -> int:
    """Normalize a parameter value to an integer."""
    if isinstance(value, str):
        return 1 if value == STATE_ON else 0

    if isinstance(value, ParameterValues):
        value = value.value

    return int(value)


@dataclass
class ParameterValues:
    """Represents a parameter values."""

    __slots__ = ("value", "min_value", "max_value")

    value: int
    min_value: int
    max_value: int


@dataclass
class ParameterDescription:
    """Represents a parameter description."""

    name: str
    unit_of_measurement: UnitOfMeasurement | Literal["%"] | None = None


@dataclass
class BinaryParameterDescription(ParameterDescription):
    """Represent a binary parameter description."""


class Parameter(ABC):
    """Represents a parameter."""

    __slots__ = ("device", "values", "description", "_pending_update", "_index")

    device: Device
    values: ParameterValues
    description: ParameterDescription
    _pending_update: bool
    _index: int

    def __init__(
        self,
        device: Device,
        values: ParameterValues,
        description: ParameterDescription,
        index: int = 0,
    ):
        """Initialize a new parameter."""
        self.device = device
        self.values = values
        self.description = description
        self._pending_update = False
        self._index = index

    def __repr__(self) -> str:
        """Return a serializable string representation."""
        return (
            f"{self.__class__.__name__}("
            f"device={self.device.__class__.__name__}, "
            f"values={self.values}, "
            f"description={self.description}, "
            f"index={self._index})"
        )

    def _call_relational_method(self, method_to_call, other):
        """Call a specified relational method."""
        func = getattr(self.values.value, method_to_call)
        return func(_normalize_parameter_value(other))

    def __int__(self) -> int:
        """Return an integer representation of parameter's value."""
        return self.values.value

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

    async def _confirm_update(self, _: Parameter) -> None:
        """A callback for when parameter update is confirmed on
        the device.
        """
        self._pending_update = False

    async def set(self, value: ParameterValueType, retries: int = SET_RETRIES) -> bool:
        """Set a parameter value."""
        if (value := _normalize_parameter_value(value)) == self.values.value:
            return True

        if value < self.values.min_value or value > self.values.max_value:
            raise ValueError(
                f"Parameter value must be between '{self.min_value}' and '{self.max_value}'"
            )

        self.values.value = value
        self._pending_update = True
        self.device.subscribe_once(self.description.name, self._confirm_update)
        while self.pending_update:
            if retries <= 0:
                _LOGGER.error(
                    "Timed out while trying to set '%s' parameter",
                    self.description.name,
                )
                self.device.unsubscribe(self.description.name, self._confirm_update)
                return False

            await self.device.queue.put(self.request)
            await asyncio.sleep(SET_TIMEOUT)
            retries -= 1

        return True

    def set_nowait(self, value: ParameterValueType, retries: int = SET_RETRIES) -> None:
        """Set a parameter value without waiting."""
        self.device.create_task(self.set(value, retries))

    @property
    def pending_update(self) -> bool:
        """Check if parameter is pending update on the device."""
        return self._pending_update

    @property
    def value(self) -> ParameterValueType:
        """A parameter value."""
        return self.values.value

    @property
    def min_value(self) -> ParameterValueType:
        """Minimum allowed value."""
        return self.values.min_value

    @property
    def max_value(self) -> ParameterValueType:
        """Maximum allowed value."""
        return self.values.max_value

    @property
    def unit_of_measurement(self) -> UnitOfMeasurement | Literal["%"] | None:
        """A unit of measurement."""
        return self.description.unit_of_measurement

    @property
    def request(self) -> Request:
        """A request to change the parameter."""
        raise NotImplementedError


class BinaryParameter(Parameter):
    """Represents binary device parameter."""

    async def turn_on(self) -> bool:
        """Set a parameter value to 'on'.

        :return: `True` if parameter was successfully turned on, `False`
            otherwise.
        :rtype: bool
        """
        return await self.set(STATE_ON)

    async def turn_off(self) -> bool:
        """Set a parameter value to 'off'.

        :return: `True` if parameter was successfully turned off, `False`
            otherwise.
        :rtype: bool
        """
        return await self.set(STATE_OFF)

    def turn_on_nowait(self) -> None:
        """Set a parameter value to 'on' without waiting."""
        self.set_nowait(STATE_ON)

    def turn_off_nowait(self) -> None:
        """Set a parameter value to 'off' without waiting."""
        self.set_nowait(STATE_OFF)

    @property
    def value(self) -> ParameterValueType:
        """A parameter value."""
        return STATE_ON if self.values.value == 1 else STATE_OFF

    @property
    def min_value(self) -> ParameterValueType:
        """Minimum allowed value."""
        return STATE_OFF

    @property
    def max_value(self) -> ParameterValueType:
        """Maximum allowed value."""
        return STATE_ON
