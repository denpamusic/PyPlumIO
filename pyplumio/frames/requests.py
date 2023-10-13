"""Contains request frames."""
from __future__ import annotations

from typing import ClassVar

from pyplumio.const import (
    ATTR_DEVICE_INDEX,
    ATTR_INDEX,
    ATTR_OFFSET,
    ATTR_SIZE,
    ATTR_VALUE,
    FrameType,
)
from pyplumio.exceptions import FrameDataError
from pyplumio.frames import Request, Response
from pyplumio.frames.responses import DeviceAvailableResponse, ProgramVersionResponse
from pyplumio.helpers.typing import EventDataType
from pyplumio.structures.schedules import SchedulesStructure


class ProgramVersionRequest(Request):
    """Represents a program version request."""

    frame_type: ClassVar[int] = FrameType.REQUEST_PROGRAM_VERSION

    def response(self, **kwargs) -> Response | None:
        """Return a response frame."""
        return ProgramVersionResponse(recipient=self.sender, **kwargs)


class CheckDeviceRequest(Request):
    """Represents a check device request."""

    frame_type: ClassVar[int] = FrameType.REQUEST_CHECK_DEVICE

    def response(self, **kwargs) -> Response | None:
        """Return a response frame."""
        return DeviceAvailableResponse(recipient=self.sender, **kwargs)


class UIDRequest(Request):
    """Represents an UID request."""

    frame_type: ClassVar[int] = FrameType.REQUEST_UID


class PasswordRequest(Request):
    """Represents a password request."""

    frame_type: ClassVar[int] = FrameType.REQUEST_PASSWORD


class EcomaxParametersRequest(Request):
    """Represents an ecoMAX parameters request.

    Contains number of parameters and index of the first parameter.
    """

    frame_type: ClassVar[int] = FrameType.REQUEST_ECOMAX_PARAMETERS

    def create_message(self, data: EventDataType) -> bytearray:
        """Create a frame message."""
        message = bytearray()
        message.append(255)  # Number of parameters.
        message.append(0)  # Index of the first parameter.
        return message


class MixerParametersRequest(Request):
    """Represents a mixer parameters request.

    Contains number of parameters to get and index of the first
    parameter.
    """

    frame_type: ClassVar[int] = FrameType.REQUEST_MIXER_PARAMETERS

    def create_message(self, data: EventDataType) -> bytearray:
        """Create a frame message."""
        message = bytearray()
        message.append(255)  # Number of parameters.
        message.append(0)  # Index of the first parameter.
        return message


class ThermostatParametersRequest(Request):
    """Represents a thermostat parameters request.

    Contains number of parameters to get and index of the first
    parameter.
    """

    frame_type: ClassVar[int] = FrameType.REQUEST_THERMOSTAT_PARAMETERS

    def create_message(self, data: EventDataType) -> bytearray:
        """Create a frame message."""
        message = bytearray()
        message.append(255)  # Number of parameters.
        message.append(0)  # Index of the first parameter.
        return message


class DataSchemaRequest(Request):
    """Represents data schema request."""

    frame_type: ClassVar[int] = FrameType.REQUEST_DATA_SCHEMA


class SetEcomaxParameterRequest(Request):
    """Represents a request to set an ecoMAX parameter.

    Contains parameter index and new value.
    """

    frame_type: ClassVar[int] = FrameType.REQUEST_SET_ECOMAX_PARAMETER

    def create_message(self, data: EventDataType) -> bytearray:
        """Create a frame message."""
        try:
            message = bytearray()
            index = data[ATTR_INDEX]
            value = data[ATTR_VALUE]
            message.append(index)
            message.append(value)
            return message
        except (KeyError, ValueError) as e:
            raise FrameDataError from e


class SetMixerParameterRequest(Request):
    """Represents a request to set a mixer parameter.

    Contains parameter index, new value and mixer index.
    """

    frame_type: ClassVar[int] = FrameType.REQUEST_SET_MIXER_PARAMETER

    def create_message(self, data: EventDataType) -> bytearray:
        """Create a frame message."""
        try:
            index = data[ATTR_INDEX]
            value = data[ATTR_VALUE]
            mixer_index = data[ATTR_DEVICE_INDEX]
            message = bytearray()
            message.append(mixer_index)
            message.append(index)
            message.append(value)
            return message
        except (KeyError, ValueError) as e:
            raise FrameDataError from e


class SetThermostatParameterRequest(Request):
    """Represents a request to set a thermostat parameter.

    Contains parameter index, new value, parameter offset and
    parameter size.

    Parameter offset is calculated by multiplying
    thermostat index by total number of parameters available.

    For example, if total available parameters is 12,
    offset for the second thermostat is 12 (1 * 12),
    and for the third thermostat is 24 (2 * 12).
    """

    frame_type: ClassVar[int] = FrameType.REQUEST_SET_THERMOSTAT_PARAMETER

    def create_message(self, data: EventDataType) -> bytearray:
        """Create a frame message."""
        try:
            message = bytearray()
            index = data[ATTR_INDEX]
            value: int = data[ATTR_VALUE]
            offset = data[ATTR_OFFSET]
            size = data[ATTR_SIZE]
            message.append(index if offset is None else index + offset)
            message += value.to_bytes(length=size, byteorder="little")
            return message
        except (KeyError, ValueError) as e:
            raise FrameDataError from e


class EcomaxControlRequest(Request):
    """Represents an ecoMAX control request.

    Contains single binary value. 0 - means that controller should
    be turned off, 1 - means that it should be turned on.
    """

    frame_type: ClassVar[int] = FrameType.REQUEST_ECOMAX_CONTROL

    def create_message(self, data: EventDataType) -> bytearray:
        """Create a frame message."""
        try:
            message = bytearray()
            message.append(data[ATTR_VALUE])
            return message
        except KeyError as e:
            raise FrameDataError from e


class StartMasterRequest(Request):
    """Represents a request to become a master.

    Once controller receives this request, it starts sending
    periodic messages.
    """

    frame_type: ClassVar[int] = FrameType.REQUEST_START_MASTER


class StopMasterRequest(Request):
    """Represents a request to stop being a master.

    Once controller receives this request, it stops sending
    periodic messages.
    """

    frame_type: ClassVar[int] = FrameType.REQUEST_STOP_MASTER


class AlertsRequest(Request):
    """Represents an alerts request.

    Contains number of alerts to get and index of the first
    alert.
    """

    frame_type: ClassVar[int] = FrameType.REQUEST_ALERTS

    def create_message(self, data: EventDataType) -> bytearray:
        """Create a frame message."""
        message = bytearray()
        message.append(0)  # Index of the first alert.
        message.append(100)  # Number of alerts.
        return message


class SchedulesRequest(Request):
    """Represents a schedules request."""

    frame_type: ClassVar[int] = FrameType.REQUEST_SCHEDULES


class SetScheduleRequest(Request):
    """Represents a request to set a schedule."""

    frame_type: ClassVar[int] = FrameType.REQUEST_SET_SCHEDULE

    def create_message(self, data: EventDataType) -> bytearray:
        """Create a frame message."""
        return SchedulesStructure(self).encode(data)
