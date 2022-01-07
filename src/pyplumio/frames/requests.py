"""Contains request frame classes."""

from pyplumio.frame import Frame

from . import responses


class ProgramVersion(Frame):
    """ProgramVersion requests version info from ecoMAX device."""
    type_: int = 0x40

    def response(self, **args):
        """Returns corresponding response frame instance.

        Keyword arguments:
        args -- arguments to pass to response frame constructor
        """
        return responses.ProgramVersion(recipient = self.sender, **args)

class CheckDevice(Frame):
    """CheckDevice requests if device is available."""
    type_: int = 0x30

    def response(self, **args):
        """Returns corresponding response frame instance.

        Keyword arguments:
        args -- arguments to pass to response frame constructor
        """
        return responses.CheckDevice(recipient = self.sender, **args)

class UID(Frame):
    """Requests device UID."""
    type_: int = 0x39

class Password(Frame):
    """Requests service password."""
    type_: int = 0x3A

class Timezones(Frame):
    """Requests timezones."""
    type_: int = 0x36

class Parameters(Frame):
    """Requests current editable parameters."""
    type_: int = 0x31

class MixerParameters(Frame):
    """Requests current mixer parameters."""
    type_: int = 0x32

class DataStructure(Frame):
    """Requests current regulator data structure."""
    type_: int = 0x55
