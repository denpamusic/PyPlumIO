"""Contains request frame classes."""

from pyplumio.constants import DEVICE_PARAMS, MIXER_PARAMS
from pyplumio.frame import Request

from . import responses


class ProgramVersion(Request):
    """ProgramVersion requests version info from ecoMAX device.

    Attributes:
        type_ -- frame type
    """

    type_: int = 0x40

    def response(self, **kwargs):
        """Returns corresponding response frame instance.

        Keyword arguments:
            **kwargs -- arguments to pass to response frame constructor
        """
        return responses.ProgramVersion(recipient=self.sender, **kwargs)


class CheckDevice(Request):
    """CheckDevice requests if device is available.

    Attributes:
        type_ -- frame type
    """

    type_: int = 0x30

    def response(self, **kwargs):
        """Returns corresponding response frame instance.

        Keyword arguments:
            args -- arguments to pass to response frame constructor
        """
        return responses.DeviceAvailable(recipient=self.sender, **kwargs)


class UID(Request):
    """Requests device UID.

    Attributes:
        type_ -- frame type
    """

    type_: int = 0x39


class Password(Request):
    """Requests service password.

    Attributes:
        type_ -- frame type
    """

    type_: int = 0x3A


class Parameters(Request):
    """Requests current editable parameters.

    Attributes:
        type_ -- frame type
    """

    type_: int = 0x31

    def create_message(self) -> bytearray:
        """Creates SetParameter message."""

        message = bytearray()
        message.append(0xFF)  # Number of parameters.
        message.append(0x00)  # Index of parameters.
        return message


class MixerParameters(Request):
    """Requests current mixer parameters.

    Attributes:
        type_ -- frame type
    """

    type_: int = 0x32


class DataStructure(Request):
    """Requests current regulator data structure.

    Attributes:
        type_ -- frame type
    """

    type_: int = 0x55


class SetParameter(Request):
    """Changes current regulator parameter.

    Attributes:
        type_ -- frame type
    """

    type_: int = 0x33

    def create_message(self) -> bytearray:
        """Creates SetParameter message."""

        message = bytearray()
        name = self._data["name"]
        value = self._data["value"]
        if name in DEVICE_PARAMS:
            message.append(DEVICE_PARAMS.index(name))
            message.append(value)

        return message


class SetMixerParameter(Request):
    """Sets mixer parameter.

    Attributes:
        type_ -- frame type
    """

    type_: int = 0x34

    def create_message(self) -> bytearray:
        """Creates SetMixerParameter message."""

        message = bytearray()
        name = self._data["name"]
        value = self._data["value"]
        index = self._data["extra"]
        if name in MIXER_PARAMS:
            message.append(index)
            message.append(MIXER_PARAMS.index(name))
            message.append(value)

        return message


class BoilerControl(Request):
    """Changes regulator state (on/off).

    Attributes:
        type_ -- frame type
    """

    type_: int = 0x3B

    def create_message(self) -> bytearray:
        """Creates BoilerControl message."""

        message = bytearray()
        message.append(self._data["value"])

        return message


class StartMaster(Request):
    """Designates RS485 device as master.

    Attributes:
        type_ -- frame type
    """

    type_: int = 0x19


class StopMaster(Request):
    """Revokes RS485 device master status.

    Attributes:
        type_ -- frame type
    """

    type_: int = 0x18
