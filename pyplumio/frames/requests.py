"""Contains request frames."""
from __future__ import annotations

from typing import ClassVar, Optional

from pyplumio.const import (
    ATTR_DEVICE_INDEX,
    ATTR_INDEX,
    ATTR_OFFSET,
    ATTR_VALUE,
    FrameType,
)
from pyplumio.exceptions import FrameDataError
from pyplumio.frames import Request, Response
from pyplumio.frames.responses import DeviceAvailableResponse, ProgramVersionResponse
from pyplumio.helpers.typing import DeviceDataType, MessageType
from pyplumio.structures.schedules import SchedulesStructure


class ProgramVersionRequest(Request):
    """Represents program version request."""

    frame_type: ClassVar[int] = FrameType.REQUEST_PROGRAM_VERSION

    def response(self, **kwargs) -> Optional[Response]:
        """Return response frame object."""
        return ProgramVersionResponse(recipient=self.sender, **kwargs)


class CheckDeviceRequest(Request):
    """Represents check device request."""

    frame_type: ClassVar[int] = FrameType.REQUEST_CHECK_DEVICE

    def response(self, **kwargs) -> Optional[Response]:
        """Return response frame object."""
        return DeviceAvailableResponse(recipient=self.sender, **kwargs)


class UIDRequest(Request):
    """Represents uid request."""

    frame_type: ClassVar[int] = FrameType.REQUEST_UID


class PasswordRequest(Request):
    """Represents password request."""

    frame_type: ClassVar[int] = FrameType.REQUEST_PASSWORD


class EcomaxParametersRequest(Request):
    """Represents ecoMAX parameters request."""

    frame_type: ClassVar[int] = FrameType.REQUEST_ECOMAX_PARAMETERS

    def create_message(self, data: DeviceDataType) -> MessageType:
        """Create frame message."""
        message = bytearray()
        message.append(255)  # Number of parameters.
        message.append(0)  # Index of the first parameter.
        return message


class MixerParametersRequest(Request):
    """Represents mixer parameters request."""

    frame_type: ClassVar[int] = FrameType.REQUEST_MIXER_PARAMETERS

    def create_message(self, data: DeviceDataType) -> MessageType:
        """Create frame message."""
        message = bytearray()
        message.append(255)  # Number of parameters.
        message.append(0)  # Index of the first parameter.
        return message


class ThermostatParametersRequest(Request):
    """Represents thermostat parameters request."""

    frame_type: ClassVar[int] = FrameType.REQUEST_THERMOSTAT_PARAMETERS

    def create_message(self, data: DeviceDataType) -> MessageType:
        """Create frame message."""
        message = bytearray()
        message.append(255)  # Number of parameters.
        message.append(0)  # Index of the first parameter.
        return message


class DataSchemaRequest(Request):
    """Represents data schema request."""

    frame_type: ClassVar[int] = FrameType.REQUEST_DATA_SCHEMA


class SetEcomaxParameterRequest(Request):
    """Represents set ecoMAX parameter request."""

    frame_type: ClassVar[int] = FrameType.REQUEST_SET_ECOMAX_PARAMETER

    def create_message(self, data: DeviceDataType) -> MessageType:
        """Create frame message."""
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
    """Represents set mixer parameter request."""

    frame_type: ClassVar[int] = FrameType.REQUEST_SET_MIXER_PARAMETER

    def create_message(self, data: DeviceDataType) -> MessageType:
        """Create frame message."""
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
    """Represents set thermostat parameter request."""

    frame_type: ClassVar[int] = FrameType.REQUEST_SET_THERMOSTAT_PARAMETER

    def create_message(self, data: DeviceDataType) -> MessageType:
        """Create frame message."""
        try:
            message = bytearray()
            index = data[ATTR_INDEX]
            value = data[ATTR_VALUE]
            offset = data[ATTR_OFFSET]
            message.append(index if offset is None else index + offset)
            message.append(value)
            return message
        except (KeyError, ValueError) as e:
            raise FrameDataError from e


class EcomaxControlRequest(Request):
    """Represent ecoMAX control request."""

    frame_type: ClassVar[int] = FrameType.REQUEST_ECOMAX_CONTROL

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

    frame_type: ClassVar[int] = FrameType.REQUEST_START_MASTER


class StopMasterRequest(Request):
    """Represent stop master request."""

    frame_type: ClassVar[int] = FrameType.REQUEST_STOP_MASTER


class AlertsRequest(Request):
    """Represent alerts request."""

    frame_type: ClassVar[int] = FrameType.REQUEST_ALERTS

    def create_message(self, data: DeviceDataType) -> MessageType:
        """Create frame message."""
        message = bytearray()
        message.append(0)  # Index of the first alert.
        message.append(100)  # Number of alerts.
        return message


class SchedulesRequest(Request):
    """Represents schedule request."""

    frame_type: ClassVar[int] = FrameType.REQUEST_SCHEDULES


class SetScheduleRequest(Request):
    """Represents set schedule request."""

    frame_type: ClassVar[int] = FrameType.REQUEST_SET_SCHEDULE

    def create_message(self, data: DeviceDataType) -> MessageType:
        return SchedulesStructure(self).encode(data)
