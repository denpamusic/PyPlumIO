"""Contains request frame classes."""

from pyplumio.frame import Frame

from . import responses


class Request(Frame):
    """Base class for all requests frames."""

    def response(self, **args) -> Frame:  # pylint: disable=no-self-use
        """Returns instance of Frame
        for response to request, if needed.
        """
        return None


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
        return responses.CheckDevice(recipient=self.sender, **args)


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


class MixerParameters(Request):
    """Requests current mixer parameters."""

    type_: int = 0x32


class DataStructure(Request):
    """Requests current regulator data structure."""

    type_: int = 0x55
