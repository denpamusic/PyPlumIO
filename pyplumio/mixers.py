"""Contains classes for mixer support."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import util
from .frames import BROADCAST_ADDRESS, Request
from .helpers.base_device import BaseDevice
from .helpers.parameter import Parameter
from .structures.mixer_parameters import MIXER_PARAMETERS
from .structures.mixers import MIXER_DATA


class Mixer(BaseDevice):
    """Mixer device representation.

    Attributes:
        _index -- mixer index
        address -- address of device that contains mixer
    """

    def __init__(
        self,
        data: Dict[str, Any] = None,
        parameters: Dict[str, List[int]] = None,
        index: int = 0,
    ):
        """Creates device instance.

        Keyword arguments:
            data -- device data
            parameters -- editable parameters
        """
        self._index = index
        self.address = BROADCAST_ADDRESS
        super().__init__(data, parameters)

    def __repr__(self) -> str:
        """Returns serializable string representation of the class."""
        return f"""{self.__class__.__name__}(
    data = {self._data},
    parameters = {self._parameters}
    index  = {self._index}
)
""".strip()

    def __str__(self) -> str:
        """Returns string representation of the class."""
        return f"""
{self._index}:
Data:
{util.make_list(self._data)}

Parameters:
{util.make_list(self._parameters, include_keys = False)}
""".strip()

    def set_data(self, data: Dict[str, Any]) -> None:
        """Sets mixer data.

        Keyword arguments:
            data -- mixer immutable attributes
        """
        for name, value in data.items():
            if name in MIXER_DATA:
                self._data[name] = value

    def set_parameters(self, parameters: Dict[str, List[int]]) -> None:
        """Sets mixer parameters.

        Keyword arguments:
            parameters -- mixer changeable parameters
        """
        for name, parameter in parameters.items():
            if name in MIXER_PARAMETERS:
                value, min_value, max_value = parameter
                self._parameters[name] = Parameter(
                    name, value, min_value, max_value, self._index
                )

    @property
    def editable_parameters(self) -> List[str]:
        """Returns list of editable parameters."""
        return MIXER_PARAMETERS


class MixersCollection:
    """Collection of mixer devices.

    Attributes:
        _address -- address of device that contains mixers from collection
        _mixers -- collection of mixers
    """

    def __init__(self, address: int = BROADCAST_ADDRESS, mixers: List[Mixer] = None):
        """Creates mixer collection instance.

        Keyword arguments:
            address -- address of device that contains mixers from collection
            data -- device data
            parameters -- editable parameters
        """
        self._address = address
        self._mixers = mixers if mixers is not None else []

    def __repr__(self) -> str:
        """Returns serializable string representation of the class."""
        return f"""MixersCollection(
    address = {self._address},
    mixers = {self._mixers}
)
""".strip()

    def __str__(self) -> str:
        """Returns string representation of the class."""
        output = ""
        for mixer in self._mixers:
            mixer_string = mixer.__str__().replace("\n", "\n    ")
            mixer_string = mixer_string.replace("\n    \n", "\n\n")
            output += f"- {mixer_string}\n\n"

        return output.strip()

    def __len__(self) -> int:
        """Returns number of mixers in collection."""
        return len(self._mixers)

    def __call__(self, index: int) -> Optional[Mixer]:
        """Returns mixer instance by index.

        Keyword arguments:
            index -- mixer index
        """
        try:
            return self._mixers[index]
        except IndexError:
            return None

    def set_data(self, mixers: list):
        """Creates mixer instance if not exists and sets mixers data.

        Keyword arguments:
            mixers -- list of mixer data
        """
        for index, data in enumerate(mixers):
            try:
                self._mixers[index].set_data(data)
            except IndexError:
                self._mixers.append(Mixer(data=data, index=index))

    def set_parameters(self, mixers: List[Dict[str, List[int]]]):
        """Creates mixer instance if not exists and
        sets mixers parameters.

        Keyword arguments:
            mixers -- list of mixer parameters
        """
        for index, parameters in enumerate(mixers):
            try:
                self._mixers[index].set_parameters(parameters)
            except IndexError:
                self._mixers.append(Mixer(parameters=parameters, index=index))

    @property
    def mixers(self) -> List[Mixer]:
        """Returns list of mixers."""
        return self._mixers

    @property
    def queue(self) -> List[Request]:
        """Clears and returns changed parameters queue
        for every mixer.
        """
        queue = []
        for mixer in self._mixers:
            mixer.address = self._address
            queue.extend(mixer.queue)

        return queue
