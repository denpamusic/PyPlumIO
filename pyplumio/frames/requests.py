"""Contains request frames."""
from __future__ import annotations

from typing import ClassVar, Optional

from pyplumio.exceptions import FrameDataError
from pyplumio.frames import Request, RequestTypes, Response, responses
from pyplumio.helpers.typing import DeviceDataType, MessageType
from pyplumio.structures.boiler_parameters import BOILER_PARAMETERS
from pyplumio.structures.mixer_parameters import MIXER_PARAMETERS


class ProgramVersion(Request):
    """Represents program version request."""

    frame_type: ClassVar[int] = RequestTypes.PROGRAM_VERSION

    def response(self, **kwargs) -> Optional[Response]:
        """Return response frame object."""
        return responses.ProgramVersion(recipient=self.sender, **kwargs)


class CheckDevice(Request):
    """Represents check device request."""

    frame_type: ClassVar[int] = RequestTypes.CHECK_DEVICE

    def response(self, **kwargs) -> Optional[Response]:
        """Return response frame object."""
        return responses.DeviceAvailable(recipient=self.sender, **kwargs)


class UID(Request):
    """Represents uid request."""

    frame_type: ClassVar[int] = RequestTypes.UID


class Password(Request):
    """Represents password request."""

    frame_type: ClassVar[int] = RequestTypes.PASSWORD


class BoilerParameters(Request):
    """Represents boiler parameters request."""

    frame_type: ClassVar[int] = RequestTypes.BOILER_PARAMETERS

    def create_message(self, data: DeviceDataType) -> MessageType:
        """Create frame message."""
        message = bytearray()
        message.append(0xFF)  # Number of parameters.
        message.append(0x00)  # Index of parameters.
        return message


class MixerParameters(Request):
    """Represents mixer parameters request."""

    frame_type: ClassVar[int] = RequestTypes.MIXER_PARAMETERS


class DataSchema(Request):
    """Represents data schema request."""

    frame_type: ClassVar[int] = RequestTypes.DATA_SCHEMA


class SetBoilerParameter(Request):
    """Represents set boiler parameter request."""

    frame_type: ClassVar[int] = RequestTypes.SET_BOILER_PARAMETER

    def create_message(self, data: DeviceDataType) -> MessageType:
        """Create frame message."""
        try:
            message = bytearray()
            name = data["name"]
            value = data["value"]
            message.append(BOILER_PARAMETERS.index(name))
            message.append(value)
            return message
        except (KeyError, ValueError) as e:
            raise FrameDataError from e


class SetMixerParameter(Request):
    """Represents set mixer parameter request."""

    frame_type: ClassVar[int] = RequestTypes.SET_MIXER_PARAMETER

    def create_message(self, data: DeviceDataType) -> MessageType:
        """Create frame message."""
        try:
            name = data["name"]
            value = data["value"]
            index = data["extra"]
            message = bytearray()
            message.append(index)
            message.append(MIXER_PARAMETERS.index(name))
            message.append(value)
            return message
        except (KeyError, ValueError) as e:
            raise FrameDataError from e


class BoilerControl(Request):
    """Represent boiler control request."""

    frame_type: ClassVar[int] = RequestTypes.BOILER_CONTROL

    def create_message(self, data: DeviceDataType) -> MessageType:
        """Creates frame message."""
        try:
            message = bytearray()
            message.append(data["value"])
            return message
        except KeyError as e:
            raise FrameDataError from e


class StartMaster(Request):
    """Represent start master request."""

    frame_type: ClassVar[int] = RequestTypes.START_MASTER


class StopMaster(Request):
    """Represent stop master request."""

    frame_type: ClassVar[int] = RequestTypes.STOP_MASTER
