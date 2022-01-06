from pyplumio.frame import Frame

from . import responses


class ProgramVersion(Frame):
    type_: int = 0x40

    def response(self, **args):
        return responses.ProgramVersion(recipient = self.sender, **args)

class CheckDevice(Frame):
    type_: int = 0x30

    def response(self, **args):
        return responses.CheckDevice(recipient = self.sender, **args)

class UID(Frame):
    type_: int = 0x39

class Password(Frame):
    type_: int = 0x3A

class Timezones(Frame):
    type_: int = 0x36

class Parameters(Frame):
    type_: int = 0x31

class MixerParameters(Frame):
    type_: int = 0x32

class DataStructure(Frame):
    type_: int = 0x55
