"""Contains request frame classes."""

from pyplumio.structures.device_parameters import DEVICE_PARAMETERS
from pyplumio.structures.mixer_parameters import MIXER_PARAMETERS

from . import Request, responses


class ProgramVersion(Request):
    """ProgramVersion requests version info from ecoMAX device.

    Attributes:
        frame_type -- frame type
    """

    frame_type: int = 0x40

    def response(self, **kwargs):
        """Returns corresponding response frame instance.

        Keyword arguments:
            **kwargs -- arguments to pass to response frame constructor
        """
        return responses.ProgramVersion(recipient=self.sender, **kwargs)


class CheckDevice(Request):
    """CheckDevice requests if device is available.

    Attributes:
        frame_type -- frame type
    """

    frame_type: int = 0x30

    def response(self, **kwargs):
        """Returns corresponding response frame instance.

        Keyword arguments:
            args -- arguments to pass to response frame constructor
        """
        return responses.DeviceAvailable(recipient=self.sender, **kwargs)


class UID(Request):
    """Requests device UID.

    Attributes:
        frame_type -- frame type
    """

    frame_type: int = 0x39


class Password(Request):
    """Requests service password.

    Attributes:
        frame_type -- frame type
    """

    frame_type: int = 0x3A


class BoilerParameters(Request):
    """Requests current editable parameters.

    Attributes:
        frame_type -- frame type
    """

    frame_type: int = 0x31

    def create_message(self) -> bytearray:
        """Creates BoilerParameters message."""

        message = bytearray()
        message.append(0xFF)  # Number of parameters.
        message.append(0x00)  # Index of parameters.
        return message


class MixerParameters(Request):
    """Requests current mixer parameters.

    Attributes:
        frame_type -- frame type
    """

    frame_type: int = 0x32


class DataSchema(Request):
    """Requests current regulator data structure.

    Attributes:
        frame_type -- frame type
    """

    frame_type: int = 0x55


class SetBoilerParameter(Request):
    """Changes current regulator parameter.

    Attributes:
        frame_type -- frame type
    """

    frame_type: int = 0x33

    def create_message(self) -> bytearray:
        """Creates SetBoilerParameter message."""

        message = bytearray()
        name = self._data["name"]
        value = self._data["value"]
        if name in DEVICE_PARAMETERS:
            message.append(DEVICE_PARAMETERS.index(name))
            message.append(value)

        return message


class SetMixerParameter(Request):
    """Sets mixer parameter.

    Attributes:
        frame_type -- frame type
    """

    frame_type: int = 0x34

    def create_message(self) -> bytearray:
        """Creates SetMixerParameter message."""

        message = bytearray()
        name = self._data["name"]
        value = self._data["value"]
        index = self._data["extra"]
        if name in MIXER_PARAMETERS:
            message.append(index)
            message.append(MIXER_PARAMETERS.index(name))
            message.append(value)

        return message


class BoilerControl(Request):
    """Changes regulator state (on/off).

    Attributes:
        frame_type -- frame type
    """

    frame_type: int = 0x3B

    def create_message(self) -> bytearray:
        """Creates BoilerControl message."""

        message = bytearray()
        message.append(self._data["value"])

        return message


class StartMaster(Request):
    """Designates RS485 device as master.

    Attributes:
        frame_type -- frame type
    """

    frame_type: int = 0x19


class StopMaster(Request):
    """Revokes RS485 device master status.

    Attributes:
        frame_type -- frame type
    """

    frame_type: int = 0x18
