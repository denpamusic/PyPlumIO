"""Contains request frames."""
from __future__ import annotations

from typing import ClassVar

from pyplumio.const import (
    ATTR_COUNT,
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

    __slots__ = ()

    frame_type: ClassVar[FrameType | int] = FrameType.REQUEST_PROGRAM_VERSION

    def response(self, **kwargs) -> Response | None:
        """Return a response frame."""
        return ProgramVersionResponse(recipient=self.sender, **kwargs)


class CheckDeviceRequest(Request):
    """Represents a check device request."""

    __slots__ = ()

    frame_type: ClassVar[FrameType | int] = FrameType.REQUEST_CHECK_DEVICE

    def response(self, **kwargs) -> Response | None:
        """Return a response frame."""
        return DeviceAvailableResponse(recipient=self.sender, **kwargs)


class UIDRequest(Request):
    """Represents an UID request."""

    __slots__ = ()

    frame_type: ClassVar[FrameType | int] = FrameType.REQUEST_UID


class PasswordRequest(Request):
    """Represents a password request."""

    __slots__ = ()

    frame_type: ClassVar[FrameType | int] = FrameType.REQUEST_PASSWORD


class EcomaxParametersRequest(Request):
    """Represents an ecoMAX parameters request.

    Contains number of parameters and index of the first parameter.
    """

    __slots__ = ()

    frame_type: ClassVar[FrameType | int] = FrameType.REQUEST_ECOMAX_PARAMETERS

    def create_message(self, data: EventDataType) -> bytearray:
        """Create a frame message."""
        return bytearray([data.get(ATTR_COUNT, 255), data.get(ATTR_INDEX, 0)])


class MixerParametersRequest(Request):
    """Represents a mixer parameters request.

    Contains number of parameters to get and index of the first
    parameter.
    """

    __slots__ = ()

    frame_type: ClassVar[FrameType | int] = FrameType.REQUEST_MIXER_PARAMETERS

    def create_message(self, data: EventDataType) -> bytearray:
        """Create a frame message."""
        return bytearray([data.get(ATTR_COUNT, 255), data.get(ATTR_INDEX, 0)])


class ThermostatParametersRequest(Request):
    """Represents a thermostat parameters request.

    Contains number of parameters to get and index of the first
    parameter.
    """

    __slots__ = ()

    frame_type: ClassVar[FrameType | int] = FrameType.REQUEST_THERMOSTAT_PARAMETERS

    def create_message(self, data: EventDataType) -> bytearray:
        """Create a frame message."""
        return bytearray([data.get(ATTR_COUNT, 255), data.get(ATTR_INDEX, 0)])


class RegulatorDataSchemaRequest(Request):
    """Represents regulator data schema request."""

    __slots__ = ()

    frame_type: ClassVar[FrameType | int] = FrameType.REQUEST_REGULATOR_DATA_SCHEMA


class SetEcomaxParameterRequest(Request):
    """Represents a request to set an ecoMAX parameter.

    Contains parameter index and new value.
    """

    __slots__ = ()

    frame_type: ClassVar[FrameType | int] = FrameType.REQUEST_SET_ECOMAX_PARAMETER

    def create_message(self, data: EventDataType) -> bytearray:
        """Create a frame message."""
        try:
            return bytearray([data[ATTR_INDEX], data[ATTR_VALUE]])
        except (KeyError, ValueError) as e:
            raise FrameDataError from e


class SetMixerParameterRequest(Request):
    """Represents a request to set a mixer parameter.

    Contains parameter index, new value and mixer index.
    """

    __slots__ = ()

    frame_type: ClassVar[FrameType | int] = FrameType.REQUEST_SET_MIXER_PARAMETER

    def create_message(self, data: EventDataType) -> bytearray:
        """Create a frame message."""
        try:
            return bytearray(
                [data[ATTR_DEVICE_INDEX], data[ATTR_INDEX], data[ATTR_VALUE]]
            )
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

    __slots__ = ()

    frame_type: ClassVar[FrameType | int] = FrameType.REQUEST_SET_THERMOSTAT_PARAMETER

    def create_message(self, data: EventDataType) -> bytearray:
        """Create a frame message."""
        try:
            index = data[ATTR_INDEX]
            value: int = data[ATTR_VALUE]
            offset = data[ATTR_OFFSET]
            message = bytearray([index if offset is None else index + offset])
            return message + value.to_bytes(length=data[ATTR_SIZE], byteorder="little")
        except (KeyError, ValueError) as e:
            raise FrameDataError from e


class EcomaxControlRequest(Request):
    """Represents an ecoMAX control request.

    Contains single binary value. 0 - means that controller should
    be turned off, 1 - means that it should be turned on.
    """

    __slots__ = ()

    frame_type: ClassVar[FrameType | int] = FrameType.REQUEST_ECOMAX_CONTROL

    def create_message(self, data: EventDataType) -> bytearray:
        """Create a frame message."""
        try:
            return bytearray([data[ATTR_VALUE]])
        except KeyError as e:
            raise FrameDataError from e


class StartMasterRequest(Request):
    """Represents a request to become a master.

    Once controller receives this request, it starts sending
    periodic messages.
    """

    __slots__ = ()

    frame_type: ClassVar[FrameType | int] = FrameType.REQUEST_START_MASTER


class StopMasterRequest(Request):
    """Represents a request to stop being a master.

    Once controller receives this request, it stops sending
    periodic messages.
    """

    __slots__ = ()

    frame_type: ClassVar[FrameType | int] = FrameType.REQUEST_STOP_MASTER


class AlertsRequest(Request):
    """Represents an alerts request.

    Contains number of alerts to get and index of the first
    alert.
    """

    __slots__ = ()

    frame_type: ClassVar[FrameType | int] = FrameType.REQUEST_ALERTS

    def create_message(self, data: EventDataType) -> bytearray:
        """Create a frame message."""

        return bytearray([data.get(ATTR_INDEX, 0), data.get(ATTR_COUNT, 10)])


class SchedulesRequest(Request):
    """Represents a schedules request."""

    __slots__ = ()

    frame_type: ClassVar[FrameType | int] = FrameType.REQUEST_SCHEDULES


class SetScheduleRequest(Request):
    """Represents a request to set a schedule."""

    __slots__ = ()

    frame_type: ClassVar[FrameType | int] = FrameType.REQUEST_SET_SCHEDULE

    def create_message(self, data: EventDataType) -> bytearray:
        """Create a frame message."""
        return SchedulesStructure(self).encode(data)
