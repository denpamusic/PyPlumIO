"""Contains request frames."""
from __future__ import annotations

from typing import ClassVar, Optional

from pyplumio.const import ATTR_EXTRA, ATTR_NAME, ATTR_VALUE
from pyplumio.exceptions import FrameDataError
from pyplumio.frames import FrameTypes, Request, Response
from pyplumio.frames.responses import DeviceAvailableResponse, ProgramVersionResponse
from pyplumio.helpers.typing import DeviceDataType, MessageType
from pyplumio.structures.boiler_parameters import BOILER_PARAMETERS
from pyplumio.structures.mixer_parameters import MIXER_PARAMETERS
from pyplumio.structures.schedules import SchedulesStructure


class ProgramVersionRequest(Request):
    """Represents program version request."""

    frame_type: ClassVar[int] = FrameTypes.REQUEST_PROGRAM_VERSION

    def response(self, **kwargs) -> Optional[Response]:
        """Return response frame object."""
        return ProgramVersionResponse(recipient=self.sender, **kwargs)


class CheckDeviceRequest(Request):
    """Represents check device request."""

    frame_type: ClassVar[int] = FrameTypes.REQUEST_CHECK_DEVICE

    def response(self, **kwargs) -> Optional[Response]:
        """Return response frame object."""
        return DeviceAvailableResponse(recipient=self.sender, **kwargs)


class UIDRequest(Request):
    """Represents uid request."""

    frame_type: ClassVar[int] = FrameTypes.REQUEST_UID


class PasswordRequest(Request):
    """Represents password request."""

    frame_type: ClassVar[int] = FrameTypes.REQUEST_PASSWORD


class BoilerParametersRequest(Request):
    """Represents boiler parameters request."""

    frame_type: ClassVar[int] = FrameTypes.REQUEST_BOILER_PARAMETERS

    def create_message(self, data: DeviceDataType) -> MessageType:
        """Create frame message."""
        message = bytearray()
        message.append(255)  # Number of parameters.
        message.append(0)  # Index of the first parameter.
        return message


class MixerParametersRequest(Request):
    """Represents mixer parameters request."""

    frame_type: ClassVar[int] = FrameTypes.REQUEST_MIXER_PARAMETERS


class DataSchemaRequest(Request):
    """Represents data schema request."""

    frame_type: ClassVar[int] = FrameTypes.REQUEST_DATA_SCHEMA


class SetBoilerParameterRequest(Request):
    """Represents set boiler parameter request."""

    frame_type: ClassVar[int] = FrameTypes.REQUEST_SET_BOILER_PARAMETER

    def create_message(self, data: DeviceDataType) -> MessageType:
        """Create frame message."""
        try:
            message = bytearray()
            name = data[ATTR_NAME]
            value = data[ATTR_VALUE]
            message.append(BOILER_PARAMETERS.index(name))
            message.append(value)
            return message
        except (KeyError, ValueError) as e:
            raise FrameDataError from e


class SetMixerParameterRequest(Request):
    """Represents set mixer parameter request."""

    frame_type: ClassVar[int] = FrameTypes.REQUEST_SET_MIXER_PARAMETER

    def create_message(self, data: DeviceDataType) -> MessageType:
        """Create frame message."""
        try:
            name = data[ATTR_NAME]
            value = data[ATTR_VALUE]
            index = data[ATTR_EXTRA]
            message = bytearray()
            message.append(index)
            message.append(MIXER_PARAMETERS.index(name))
            message.append(value)
            return message
        except (KeyError, ValueError) as e:
            raise FrameDataError from e


class BoilerControlRequest(Request):
    """Represent boiler control request."""

    frame_type: ClassVar[int] = FrameTypes.REQUEST_BOILER_CONTROL

    def create_message(self, data: DeviceDataType) -> MessageType:
        """Creates frame message."""
        try:
            message = bytearray()
            message.append(data[ATTR_VALUE])
            return message
        except KeyError as e:
            raise FrameDataError from e


class StartMasterRequest(Request):
    """Represent start master request."""

    frame_type: ClassVar[int] = FrameTypes.REQUEST_START_MASTER


class StopMasterRequest(Request):
    """Represent stop master request."""

    frame_type: ClassVar[int] = FrameTypes.REQUEST_STOP_MASTER


class AlertsRequest(Request):
    """Represent alerts request."""

    frame_type: ClassVar[int] = FrameTypes.REQUEST_ALERTS

    def create_message(self, data: DeviceDataType) -> MessageType:
        """Create frame message."""
        message = bytearray()
        message.append(0)  # Index of the first alarm.
        message.append(100)  # Number of alarms.
        return message


class SchedulesRequest(Request):
    """Represents schedule request."""

    frame_type: ClassVar[int] = FrameTypes.REQUEST_SCHEDULES


class SetScheduleRequest(Request):
    """Represents set schedule request."""

    frame_type: ClassVar[int] = FrameTypes.REQUEST_SET_SCHEDULE

    def create_message(self, data: DeviceDataType) -> MessageType:
        return SchedulesStructure(self).encode(data)
