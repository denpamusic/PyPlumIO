"""Contains response frames."""

from __future__ import annotations

from typing import Any

from pyplumio.const import ATTR_PASSWORD, FrameType
from pyplumio.frames import Response, Structured, frame_type
from pyplumio.structures.alerts import AlertsStructure
from pyplumio.structures.ecomax_parameters import EcomaxParametersStructure
from pyplumio.structures.mixer_parameters import MixerParametersStructure
from pyplumio.structures.network_info import NetworkInfoStructure
from pyplumio.structures.product_info import ProductInfoStructure
from pyplumio.structures.program_version import ProgramVersionStructure
from pyplumio.structures.regulator_data_schema import RegulatorDataSchemaStructure
from pyplumio.structures.schedules import SchedulesStructure
from pyplumio.structures.thermostat_parameters import ThermostatParametersStructure


@frame_type(FrameType.RESPONSE_ALERTS, structure=AlertsStructure)
class AlertsResponse(Structured, Response):
    """Represents response to a device alerts request."""

    __slots__ = ()


@frame_type(FrameType.RESPONSE_DEVICE_AVAILABLE, structure=NetworkInfoStructure)
class DeviceAvailableResponse(Structured, Response):
    """Represents a device available response.

    Contains network information and status.
    """

    __slots__ = ()


@frame_type(FrameType.RESPONSE_ECOMAX_CONTROL)
class EcomaxControlResponse(Response):
    """Represents response to an ecoMAX control request.

    Empty response acknowledges, that ecoMAX control request was
    successfully processed.
    """

    __slots__ = ()


@frame_type(FrameType.RESPONSE_ECOMAX_PARAMETERS, structure=EcomaxParametersStructure)
class EcomaxParametersResponse(Structured, Response):
    """Represents an ecoMAX parameters response.

    Contains editable ecoMAX parameters.
    """

    __slots__ = ()


@frame_type(FrameType.RESPONSE_MIXER_PARAMETERS, structure=MixerParametersStructure)
class MixerParametersResponse(Structured, Response):
    """Represents a mixer parameters response.

    Contains editable mixer parameters.
    """

    __slots__ = ()


@frame_type(FrameType.RESPONSE_PASSWORD)
class PasswordResponse(Response):
    """Represents a password response.

    Contains device service password as plaintext.
    """

    __slots__ = ()

    def decode_message(self, message: bytearray) -> dict[str, Any]:
        """Decode a frame message."""
        password = message[1:].decode() if message[1:] else None
        return {ATTR_PASSWORD: password}


@frame_type(FrameType.RESPONSE_PROGRAM_VERSION, structure=ProgramVersionStructure)
class ProgramVersionResponse(Structured, Response):
    """Represents a program version response.

    Contains software version info.
    """

    __slots__ = ()


@frame_type(
    FrameType.RESPONSE_REGULATOR_DATA_SCHEMA, structure=RegulatorDataSchemaStructure
)
class RegulatorDataSchemaResponse(Structured, Response):
    """Represents a regulator data schema response.

    Contains schema, that describes structure of ecoMAX regulator data
    message.
    """

    __slots__ = ()


@frame_type(FrameType.RESPONSE_SCHEDULES, structure=SchedulesStructure)
class SchedulesResponse(Structured, Response):
    """Represents response to a device schedules request."""

    __slots__ = ()


@frame_type(FrameType.RESPONSE_SET_ECOMAX_PARAMETER)
class SetEcomaxParameterResponse(Response):
    """Represents response to a set ecoMAX parameter request.

    Empty response acknowledges, that ecoMAX parameter was
    successfully set.
    """

    __slots__ = ()


@frame_type(FrameType.RESPONSE_SET_MIXER_PARAMETER)
class SetMixerParameterResponse(Response):
    """Represents response to a set mixer parameter request.

    Empty response acknowledges, that mixer parameter was
    successfully set.
    """

    __slots__ = ()


@frame_type(FrameType.RESPONSE_SET_THERMOSTAT_PARAMETER)
class SetThermostatParameterResponse(Response):
    """Represents response to a set thermostat parameter request.

    Empty response acknowledges, that thermostat parameter was
    successfully set.
    """

    __slots__ = ()


@frame_type(
    FrameType.RESPONSE_THERMOSTAT_PARAMETERS, structure=ThermostatParametersStructure
)
class ThermostatParametersResponse(Structured, Response):
    """Represents a thermostat parameters response.

    Contains editable thermostat parameters.
    """

    __slots__ = ()


@frame_type(FrameType.RESPONSE_UID, structure=ProductInfoStructure)
class UIDResponse(Structured, Response):
    """Represents an UID response.

    Contains product info and product UID.
    """

    __slots__ = ()


__all__ = [
    "AlertsResponse",
    "DeviceAvailableResponse",
    "EcomaxControlResponse",
    "EcomaxParametersResponse",
    "MixerParametersResponse",
    "PasswordResponse",
    "ProgramVersionResponse",
    "RegulatorDataSchemaResponse",
    "SchedulesResponse",
    "SetEcomaxParameterResponse",
    "SetMixerParameterResponse",
    "SetThermostatParameterResponse",
    "ThermostatParametersResponse",
    "UIDResponse",
]
