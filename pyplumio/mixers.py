"""Contains classes for mixer support."""
from __future__ import annotations

from .constants import MIXER_DATA, MIXER_PARAMS
from .frame import BROADCAST_ADDRESS
from .helpers.base_device import BaseDevice
from .helpers.parameter import Parameter


class Mixer(BaseDevice):
    """Mixer device representation."""

    def __init__(self, data: dict = None, parameters: dict = None, index: int = 0):
        """Creates device instance.

        Keyword arguments:
        data -- device data
        parameters -- editable parameters
        """
        self.__dict__["address"] = BROADCAST_ADDRESS
        super().__init__(data, parameters)
        self._index = index

    def set_data(self, data: dict) -> None:
        """Sets mixer data.

        Keyword arguments:
        data -- mixer immutable attributes
        """
        for name, value in data.items():
            if name in MIXER_DATA:
                self._data[name] = value

    def set_parameters(self, parameters: dict) -> None:
        """Sets mixer parameters.

        Keyword arguments:
        parameters -- mixer changeable parameters
        """
        for name, parameter in parameters.items():
            if name in MIXER_PARAMS:
                self._parameters[name] = Parameter(name, *parameter, self._index)

    @property
    def editable_parameters(self) -> list:
        """Returns list of editable parameters."""
        return MIXER_PARAMS


class MixersCollection:
    """Collection of mixer devices."""

    def __init__(self, address: int = BROADCAST_ADDRESS, mixers: list = None):
        """Creates mixer collection instance.

        Keyword arguments:
        address -- address of device containing mixers
        data -- device data
        parameters -- editable parameters
        """
        self._address = address

        if mixers is None:
            self._mixers = []
        else:
            self._mixers = mixers

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
        for index, mixer in enumerate(self._mixers):
            mixer_string = mixer.__str__().replace("\n", "\n    ")
            output += f"- {index}:\n    {mixer_string}\n\n"

        return output

    def __len__(self) -> int:
        """Returns number of mixers in collection."""
        return len(self._mixers)

    def __call__(self, index: int) -> Mixer | None:
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

    def set_parameters(self, mixers: list):
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
    def mixers(self):
        """Returns list of mixers."""
        return self._mixers

    @property
    def queue(self):
        """Clears and returns changed parameters queue
        for every mixer.
        """
        queue = []
        for mixer in self._mixers:
            mixer.address = self._address
            queue.extend(mixer.queue)

        return queue
