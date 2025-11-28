"""Contains request frames."""

from __future__ import annotations

from typing import Any, cast

from pyplumio.const import (
    ATTR_COUNT,
    ATTR_DEVICE_INDEX,
    ATTR_INDEX,
    ATTR_OFFSET,
    ATTR_PARAMETER,
    ATTR_SCHEDULE,
    ATTR_SIZE,
    ATTR_START,
    ATTR_SWITCH,
    ATTR_TYPE,
    ATTR_VALUE,
    FrameType,
)
from pyplumio.exceptions import FrameDataError
from pyplumio.frames import Request, expect_response, frame_handler, responses
from pyplumio.structures.schedules import SCHEDULES
from pyplumio.utils import join_bits


@frame_handler(FrameType.REQUEST_ALERTS)
@expect_response(responses.AlertsResponse)
class AlertsRequest(Request):
    """Represents an alerts request.

    Contains number of alerts to get and index of the first
    alert.
    """

    __slots__ = ()

    def create_message(self, data: dict[str, Any]) -> bytearray:
        """Create a frame message."""
        return bytearray([data.get(ATTR_START, 0), data.get(ATTR_COUNT, 10)])


@frame_handler(FrameType.REQUEST_CHECK_DEVICE)
@expect_response(responses.DeviceAvailableResponse)
class CheckDeviceRequest(Request):
    """Represents a check device request."""

    __slots__ = ()


@frame_handler(FrameType.REQUEST_ECOMAX_CONTROL)
@expect_response(responses.EcomaxControlResponse)
class EcomaxControlRequest(Request):
    """Represents an ecoMAX control request.

    Contains single binary value. 0 - means that controller should
    be turned off, 1 - means that it should be turned on.
    """

    __slots__ = ()

    def create_message(self, data: dict[str, Any]) -> bytearray:
        """Create a frame message."""
        try:
            return bytearray([data[ATTR_VALUE]])
        except KeyError as e:
            raise FrameDataError from e


@frame_handler(FrameType.REQUEST_ECOMAX_PARAMETERS)
@expect_response(responses.EcomaxParametersResponse)
class EcomaxParametersRequest(Request):
    """Represents an ecoMAX parameters request.

    Contains number of parameters and index of the first parameter.
    """

    __slots__ = ()

    def create_message(self, data: dict[str, Any]) -> bytearray:
        """Create a frame message."""
        return bytearray([data.get(ATTR_COUNT, 255), data.get(ATTR_START, 0)])


@frame_handler(FrameType.REQUEST_MIXER_PARAMETERS)
@expect_response(responses.MixerParametersResponse)
class MixerParametersRequest(Request):
    """Represents a mixer parameters request.

    Contains number of parameters to get and index of the first
    parameter.
    """

    __slots__ = ()

    def create_message(self, data: dict[str, Any]) -> bytearray:
        """Create a frame message."""
        return bytearray([data.get(ATTR_COUNT, 255), data.get(ATTR_START, 0)])


@frame_handler(FrameType.REQUEST_PASSWORD)
@expect_response(responses.PasswordResponse)
class PasswordRequest(Request):
    """Represents a password request."""

    __slots__ = ()


@frame_handler(FrameType.REQUEST_PROGRAM_VERSION)
@expect_response(responses.ProgramVersionResponse)
class ProgramVersionRequest(Request):
    """Represents a program version request."""

    __slots__ = ()


@frame_handler(FrameType.REQUEST_REGULATOR_DATA_SCHEMA)
@expect_response(responses.RegulatorDataSchemaResponse)
class RegulatorDataSchemaRequest(Request):
    """Represents regulator data schema request."""

    __slots__ = ()


@frame_handler(FrameType.REQUEST_SCHEDULES)
@expect_response(responses.SchedulesResponse)
class SchedulesRequest(Request):
    """Represents a schedules request."""

    __slots__ = ()


@frame_handler(FrameType.REQUEST_SET_ECOMAX_PARAMETER)
@expect_response(responses.SetEcomaxParameterResponse)
class SetEcomaxParameterRequest(Request):
    """Represents a request to set an ecoMAX parameter.

    Contains parameter index and new value.
    """

    __slots__ = ()

    def create_message(self, data: dict[str, Any]) -> bytearray:
        """Create a frame message."""
        try:
            return bytearray([data[ATTR_INDEX], data[ATTR_VALUE]])
        except (KeyError, ValueError) as e:
            raise FrameDataError from e


@frame_handler(FrameType.REQUEST_SET_MIXER_PARAMETER)
@expect_response(responses.SetMixerParameterResponse)
class SetMixerParameterRequest(Request):
    """Represents a request to set a mixer parameter.

    Contains parameter index, new value and mixer index.
    """

    __slots__ = ()

    def create_message(self, data: dict[str, Any]) -> bytearray:
        """Create a frame message."""
        try:
            return bytearray(
                [data[ATTR_DEVICE_INDEX], data[ATTR_INDEX], data[ATTR_VALUE]]
            )
        except (KeyError, ValueError) as e:
            raise FrameDataError from e


@frame_handler(FrameType.REQUEST_SET_SCHEDULE)
class SetScheduleRequest(Request):
    """Represents a request to set a schedule."""

    __slots__ = ()

    def create_message(self, data: dict[str, Any]) -> bytearray:
        """Create a frame message."""
        message = b"\1"
        try:
            schedule_type = SCHEDULES.index(data[ATTR_TYPE])
            message += schedule_type.to_bytes(length=1, byteorder="little")
            message += int(data[ATTR_SWITCH]).to_bytes(length=1, byteorder="little")
            message += int(data[ATTR_PARAMETER]).to_bytes(length=1, byteorder="little")
            schedule = cast(list[list[bool]], data[ATTR_SCHEDULE])
        except (KeyError, ValueError) as e:
            raise FrameDataError from e

        return bytearray(message) + bytearray(
            join_bits(day[i : i + 8]) for day in schedule for i in range(0, len(day), 8)
        )


@frame_handler(FrameType.REQUEST_SET_THERMOSTAT_PARAMETER)
@expect_response(responses.SetThermostatParameterResponse)
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

    def create_message(self, data: dict[str, Any]) -> bytearray:
        """Create a frame message."""
        try:
            index = data[ATTR_INDEX]
            value: int = data[ATTR_VALUE]
            offset = data[ATTR_OFFSET]
            message = bytearray([index if offset is None else index + offset])
            return message + value.to_bytes(length=data[ATTR_SIZE], byteorder="little")
        except (KeyError, ValueError) as e:
            raise FrameDataError from e


@frame_handler(FrameType.REQUEST_START_MASTER)
class StartMasterRequest(Request):
    """Represents a request to become a master.

    Once controller receives this request, it starts sending
    periodic messages.
    """

    __slots__ = ()


@frame_handler(FrameType.REQUEST_STOP_MASTER)
class StopMasterRequest(Request):
    """Represents a request to stop being a master.

    Once controller receives this request, it stops sending
    periodic messages.
    """

    __slots__ = ()


@frame_handler(FrameType.REQUEST_THERMOSTAT_PARAMETERS)
@expect_response(responses.ThermostatParametersResponse)
class ThermostatParametersRequest(Request):
    """Represents a thermostat parameters request.

    Contains number of parameters to get and index of the first
    parameter.
    """

    __slots__ = ()

    def create_message(self, data: dict[str, Any]) -> bytearray:
        """Create a frame message."""
        return bytearray([data.get(ATTR_COUNT, 255), data.get(ATTR_START, 0)])


@frame_handler(FrameType.REQUEST_UID)
@expect_response(responses.UIDResponse)
class UIDRequest(Request):
    """Represents an UID request."""

    __slots__ = ()


__all__ = [
    "AlertsRequest",
    "CheckDeviceRequest",
    "EcomaxControlRequest",
    "EcomaxParametersRequest",
    "MixerParametersRequest",
    "PasswordRequest",
    "ProgramVersionRequest",
    "RegulatorDataSchemaRequest",
    "SchedulesRequest",
    "SetEcomaxParameterRequest",
    "SetMixerParameterRequest",
    "SetScheduleRequest",
    "SetThermostatParameterRequest",
    "StartMasterRequest",
    "StopMasterRequest",
    "ThermostatParametersRequest",
    "UIDRequest",
]
