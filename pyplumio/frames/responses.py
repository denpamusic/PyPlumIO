"""Contains response frames."""
from __future__ import annotations

from typing import ClassVar

from pyplumio.const import ATTR_PASSWORD, FrameType
from pyplumio.frames import Response
from pyplumio.helpers.typing import EventDataType
from pyplumio.structures.alerts import AlertsStructure
from pyplumio.structures.ecomax_parameters import EcomaxParametersStructure
from pyplumio.structures.mixer_parameters import MixerParametersStructure
from pyplumio.structures.network_info import NetworkInfoStructure
from pyplumio.structures.product_info import ProductInfoStructure
from pyplumio.structures.program_version import ProgramVersionStructure
from pyplumio.structures.regulator_data_schema import RegulatorDataSchemaStructure
from pyplumio.structures.schedules import SchedulesStructure
from pyplumio.structures.thermostat_parameters import ThermostatParametersStructure


class ProgramVersionResponse(Response):
    """Represents a program version response.

    Contains software version info.
    """

    __slots__ = ()

    frame_type: ClassVar[FrameType | int] = FrameType.RESPONSE_PROGRAM_VERSION

    def create_message(self, data: EventDataType) -> bytearray:
        """Create a frame message."""
        return ProgramVersionStructure(self).encode(data)

    def decode_message(self, message: bytearray) -> EventDataType:
        """Decode a frame message."""
        return ProgramVersionStructure(self).decode(message)[0]


class DeviceAvailableResponse(Response):
    """Represents a device available response.

    Contains network information and status.
    """

    __slots__ = ()

    frame_type: ClassVar[FrameType | int] = FrameType.RESPONSE_DEVICE_AVAILABLE

    def create_message(self, data: EventDataType) -> bytearray:
        """Create a frame message."""
        return NetworkInfoStructure(self).encode(data)

    def decode_message(self, message: bytearray) -> EventDataType:
        """Decode a frame message."""
        return NetworkInfoStructure(self).decode(message, offset=1)[0]


class UIDResponse(Response):
    """Represents an UID response.

    Contains product info and product UID.
    """

    __slots__ = ()

    frame_type: ClassVar[FrameType | int] = FrameType.RESPONSE_UID

    def create_message(self, data: EventDataType) -> bytearray:
        """Create a frame message."""
        return ProductInfoStructure(self).encode(data)

    def decode_message(self, message: bytearray) -> EventDataType:
        """Decode a frame message."""
        return ProductInfoStructure(self).decode(message)[0]


class PasswordResponse(Response):
    """Represents a password response.

    Contains device service password as plaintext.
    """

    __slots__ = ()

    frame_type: ClassVar[FrameType | int] = FrameType.RESPONSE_PASSWORD

    def decode_message(self, message: bytearray) -> EventDataType:
        """Decode a frame message."""
        password = message[1:].decode() if message[1:] else None
        return {ATTR_PASSWORD: password}


class EcomaxParametersResponse(Response):
    """Represents an ecoMAX parameters response.

    Contains editable ecoMAX parameters.
    """

    __slots__ = ()

    frame_type: ClassVar[FrameType | int] = FrameType.RESPONSE_ECOMAX_PARAMETERS

    def decode_message(self, message: bytearray) -> EventDataType:
        """Decode a frame message."""
        return EcomaxParametersStructure(self).decode(message)[0]


class MixerParametersResponse(Response):
    """Represents a mixer parameters response.

    Contains editable mixer parameters.
    """

    __slots__ = ()

    frame_type: ClassVar[FrameType | int] = FrameType.RESPONSE_MIXER_PARAMETERS

    def decode_message(self, message: bytearray) -> EventDataType:
        """Decode a frame message."""
        return MixerParametersStructure(self).decode(message)[0]


class ThermostatParametersResponse(Response):
    """Represents a thermostat parameters response.

    Contains editable thermostat parameters.
    """

    __slots__ = ()

    frame_type: ClassVar[FrameType | int] = FrameType.RESPONSE_THERMOSTAT_PARAMETERS

    def decode_message(self, message: bytearray) -> EventDataType:
        """Decode a frame message."""
        return ThermostatParametersStructure(self).decode(message)[0]


class RegulatorDataSchemaResponse(Response):
    """Represents a regulator data schema response.

    Contains schema, that describes structure of ecoMAX regulator data
    message.
    """

    __slots__ = ()

    frame_type: ClassVar[FrameType | int] = FrameType.RESPONSE_REGULATOR_DATA_SCHEMA

    def decode_message(self, message: bytearray) -> EventDataType:
        """Decode a frame message."""
        return RegulatorDataSchemaStructure(self).decode(message)[0]


class SetEcomaxParameterResponse(Response):
    """Represents response to a set ecoMAX parameter request.

    Empty response acknowledges, that ecoMAX parameter was
    successfully set.
    """

    __slots__ = ()

    frame_type: ClassVar[FrameType | int] = FrameType.RESPONSE_SET_ECOMAX_PARAMETER


class SetMixerParameterResponse(Response):
    """Represents response to a set mixer parameter request.

    Empty response acknowledges, that mixer parameter was
    successfully set.
    """

    __slots__ = ()

    frame_type: ClassVar[FrameType | int] = FrameType.RESPONSE_SET_MIXER_PARAMETER


class SetThermostatParameterResponse(Response):
    """Represents response to a set thermostat parameter request.

    Empty response acknowledges, that thermostat parameter was
    successfully set.
    """

    __slots__ = ()

    frame_type: ClassVar[FrameType | int] = FrameType.RESPONSE_SET_THERMOSTAT_PARAMETER


class EcomaxControlResponse(Response):
    """Represents response to an ecoMAX control request.

    Empty response acknowledges, that ecoMAX control request was
    successfully processed.
    """

    __slots__ = ()

    frame_type: ClassVar[FrameType | int] = FrameType.RESPONSE_ECOMAX_CONTROL


class AlertsResponse(Response):
    """Represents response to a device alerts request."""

    __slots__ = ()

    frame_type: ClassVar[FrameType | int] = FrameType.RESPONSE_ALERTS

    def decode_message(self, message: bytearray) -> EventDataType:
        """Decode a frame message."""
        return AlertsStructure(self).decode(message)[0]


class SchedulesResponse(Response):
    """Represents response to a device schedules request."""

    __slots__ = ()

    frame_type: ClassVar[FrameType | int] = FrameType.RESPONSE_SCHEDULES

    def decode_message(self, message: bytearray) -> EventDataType:
        """Decode a frame message."""
        return SchedulesStructure(self).decode(message)[0]
