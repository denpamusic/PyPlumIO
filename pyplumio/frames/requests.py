"""Contains request frames."""
from __future__ import annotations

from pyplumio.exceptions import FrameDataError
from pyplumio.frames import Request, responses
from pyplumio.structures.boiler_parameters import BOILER_PARAMETERS
from pyplumio.structures.mixer_parameters import MIXER_PARAMETERS


class ProgramVersion(Request):
    """Represents program version request."""

    frame_type: int = 0x40

    def response(self, **kwargs):
        """Return response frame object."""
        return responses.ProgramVersion(recipient=self.sender, **kwargs)


class CheckDevice(Request):
    """Represents check device request."""

    frame_type: int = 0x30

    def response(self, **kwargs):
        """Return response frame object."""
        return responses.DeviceAvailable(recipient=self.sender, **kwargs)


class UID(Request):
    """Represents uid request."""

    frame_type: int = 0x39


class Password(Request):
    """Represents password request."""

    frame_type: int = 0x3A


class BoilerParameters(Request):
    """Represents boiler parameters request."""

    frame_type: int = 0x31

    def create_message(self) -> bytearray:
        """Create frame message."""
        message = bytearray()
        message.append(0xFF)  # Number of parameters.
        message.append(0x00)  # Index of parameters.
        return message


class MixerParameters(Request):
    """Represents mixer parameters request."""

    frame_type: int = 0x32


class DataSchema(Request):
    """Represents data schema request."""

    frame_type: int = 0x55


class SetBoilerParameter(Request):
    """Represents set boiler parameter request."""

    frame_type: int = 0x33

    def create_message(self) -> bytearray:
        """Create frame message."""
        message = bytearray()

        if self._data is not None and "name" in self._data and "value" in self._data:
            name = self.data["name"]
            value = self.data["value"]

            if name in BOILER_PARAMETERS:
                message.append(BOILER_PARAMETERS.index(name))
                message.append(value)

            return message

        raise FrameDataError()


class SetMixerParameter(Request):
    """Represents set mixer parameter request."""

    frame_type: int = 0x34

    def create_message(self) -> bytearray:
        """Create frame message."""
        message = bytearray()
        if (
            self._data is not None
            and "name" in self.data
            and "value" in self.data
            and "extra" in self.data
        ):
            name = self.data["name"]
            value = self.data["value"]
            index = self.data["extra"]
            if name in MIXER_PARAMETERS:
                message.append(index)
                message.append(MIXER_PARAMETERS.index(name))
                message.append(value)

            return message

        raise FrameDataError()


class BoilerControl(Request):
    """Represent boiler control request."""

    frame_type: int = 0x3B

    def create_message(self) -> bytearray:
        """Creates frame message."""
        message = bytearray()
        if self._data is not None and "value" in self.data:
            message.append(self.data["value"])

            return message

        raise FrameDataError()


class StartMaster(Request):
    """Represent start master request."""

    frame_type: int = 0x19


class StopMaster(Request):
    """Represent stop master request."""

    frame_type: int = 0x18
