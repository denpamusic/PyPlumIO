"""Contains request frame classes."""

from pyplumio.constants import EDITABLE_PARAMS
from pyplumio.frame import Request

from . import responses


class ProgramVersion(Request):
    """ProgramVersion requests version info from ecoMAX device."""

    type_: int = 0x40

    def response(self, **args):
        """Returns corresponding response frame instance.

        Keyword arguments:
        args -- arguments to pass to response frame constructor
        """
        return responses.ProgramVersion(recipient=self.sender, **args)


class CheckDevice(Request):
    """CheckDevice requests if device is available."""

    type_: int = 0x30

    def response(self, **args):
        """Returns corresponding response frame instance.

        Keyword arguments:
        args -- arguments to pass to response frame constructor
        """
        return responses.DeviceAvailable(recipient=self.sender, **args)


class UID(Request):
    """Requests device UID."""

    type_: int = 0x39


class Password(Request):
    """Requests service password."""

    type_: int = 0x3A


class Timezones(Request):
    """Requests timezones."""

    type_: int = 0x36


class Parameters(Request):
    """Requests current editable parameters."""

    type_: int = 0x31

    def create_message(self) -> bytearray:
        """Creates SetParameter message."""

        message = bytearray()
        message.append(0xFF)  # Number of parameters.
        message.append(0x00)  # Index of parameters.
        return message


class MixerParameters(Request):
    """Requests current mixer parameters."""

    type_: int = 0x32


class DataStructure(Request):
    """Requests current regulator data structure."""

    type_: int = 0x55


class SetParameter(Request):
    """Changes current regulator parameter."""

    type_: int = 0x33

    def create_message(self) -> bytearray:
        """Creates SetParameter message."""

        message = bytearray()
        name = self._data["name"]
        value = self._data["value"]
        if name in EDITABLE_PARAMS:
            message.append(EDITABLE_PARAMS.index(name))
            message.append(value)

        return message


class BoilerControl(Request):
    """Changes regulator state (on/off)."""

    type_: int = 0x3B

    def create_message(self) -> bytearray:
        """Creates BoilerControl message."""

        message = bytearray()
        message.append(self._data["value"])

        return message
