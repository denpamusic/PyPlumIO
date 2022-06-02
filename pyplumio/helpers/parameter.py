"""Contains device parameter representation."""

from pyplumio.frames import Request
from pyplumio.frames.requests import (
    BoilerControl,
    SetBoilerParameter,
    SetMixerParameter,
)
from pyplumio.structures.mixer_parameters import MIXER_PARAMETERS


class Parameter:
    """Device parameter representation.

    Attributes:
        name -- parameter name
        value -- parameter value
        min_value -- minimum acceptable value
        max_value -- maximum acceptable value
        extra -- extra information
    """

    def __init__(
        self, name: str, value: int, min_value: int, max_value: int, extra=None
    ):
        """Creates parameter.

        Keyword attributes:
            name -- parameter name
            value -- parameter value
            min_value -- minimum acceptable value
            max_value -- maximum acceptable value
            extra -- extra information
        """
        self.name = name
        self.value = int(value)
        self.min_value = min_value
        self.max_value = max_value
        self.extra = extra

    def set(self, value) -> None:
        """Sets parameter value.

        Keyword arguments:
            value -- new value to set parameter to
        """
        if self.value != value and self.min_value <= value <= self.max_value:
            self.value = value

    @property
    def request(self) -> Request:
        """Returns request to change parameter."""
        if self.name == "boiler_control":
            return BoilerControl(data=self.__dict__)

        if self.name in MIXER_PARAMETERS:
            return SetMixerParameter(data=self.__dict__)

        return SetBoilerParameter(data=self.__dict__)

    def __repr__(self) -> str:
        """Returns serializable string representation."""
        return f"""Parameter(
    name = {self.name},
    value = {self.value},
    min_value = {self.min_value},
    max_value = {self.max_value},
    extra = {self.extra}
)""".strip()

    def __str__(self) -> str:
        """Returns string representation."""
        return f"{self.name}: {self.value} (range {self.min_value} - {self.max_value})"

    def __int__(self) -> int:
        """Returns integer representation of parameter value.

        Keyword arguments:
            other -- other value to compare to
        """
        return int(self.value)

    def __eq__(self, other) -> bool:
        """Compares if parameter value is equal to other.

        Keyword arguments:
            other -- other value to compare to
        """
        return self.value == other

    def __ge__(self, other) -> int:
        """Compares if parameter value is greater or equal to other.

        Keyword arguments:
            other -- other value to compare to
        """
        return self.value >= other

    def __gt__(self, other) -> int:
        """Compares if parameter value is greater than other.

        Keyword arguments:
            other -- other value to compare to
        """
        return self.value > other

    def __le__(self, other) -> int:
        """Compares if parameter value is less or equal to other.

        Keyword arguments:
            other -- other value to compare to
        """
        return self.value <= other

    def __lt__(self, other) -> int:
        """Compares if parameter value is less that other.

        Keyword arguments:
            other -- other value to compare to
        """
        return self.value < other
