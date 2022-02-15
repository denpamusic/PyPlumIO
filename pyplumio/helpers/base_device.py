"""Contains base device class."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple

from pyplumio import util
from pyplumio.exceptions import UninitializedParameterError
from pyplumio.frame import BROADCAST_ADDRESS, Request

from .parameter import Parameter


class BaseDevice(ABC):
    """Base device class.

    Attributes:
        _data -- contains immutable device data
        _parameters --  contains editable parameters
    """

    address: int = BROADCAST_ADDRESS

    def __init__(
        self, data: Dict[str, Any] = None, parameters: Dict[str, List[int]] = None
    ):
        """Creates device instance.

        Keyword arguments:
            data -- device data
            parameters -- editable parameters
        """
        self.__dict__["_data"] = {}
        self.__dict__["_parameters"] = {}

        if data is not None:
            self.set_data(data)

        if parameters is not None:
            self.set_parameters(parameters)

        self._queue: List[Request] = []

    def __getattr__(self, name: str):
        """Gets data or parameter as class attribute.

        Keyword arguments:
            name -- name of property to get
        """
        key = name.lower()
        if key in self._data:
            return self._data[key]

        if key in self._parameters:
            return self._parameters[key]

        raise AttributeError

    def __setattr__(self, name: str, value) -> None:
        """Sets class attribute or device parameter.

        Keyword arguments:
            name -- attribute name
            value -- attribute value
        """
        key = name.lower()
        if key in self._data:
            raise AttributeError()

        if key not in self.editable_parameters:
            self.__dict__[name] = value

        elif key in self._parameters:
            self._parameters[key].set(value)
            request = self._parameters[key].request
            request.recipient = self.address
            self._queue.append(request)

        else:
            raise UninitializedParameterError()

    def __repr__(self) -> str:
        """Returns serializable string representation of the class."""
        return f"""{self.__class__.__name__}(
    data = {self._data},
    parameters = {self._parameters}
)
""".strip()

    def __str__(self) -> str:
        """Returns string representation of the class."""
        return f"""
Data:
{util.make_list(self._data)}

Parameters:
{util.make_list(self._parameters, include_keys = False)}
""".strip()

    @property
    def queue(self) -> List[Request]:
        """Clears and returns changed parameters queue."""
        queue = self._queue
        self._queue = []
        return queue

    @property
    def data(self) -> Dict[str, Any]:
        """Returns device data."""
        return self._data

    @property
    def parameters(self) -> Dict[str, Parameter]:
        """Returns device parameters."""
        return self._parameters

    @abstractmethod
    def set_data(self, data: Dict[str, Any]) -> None:
        """Sets device data.

        Keyword arguments:
            data -- device immutable attributes
        """

    @abstractmethod
    def set_parameters(self, parameters: Dict[str, List[int]]) -> None:
        """Sets device parameters.

        Keyword arguments:
            parameters -- device changeable parameters
        """

    @property
    @abstractmethod
    def editable_parameters(self) -> Tuple[str, ...]:
        """Returns tuple of editable parameters."""
