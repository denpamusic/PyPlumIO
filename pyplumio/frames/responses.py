"""Contains response frames."""
from __future__ import annotations

from typing import ClassVar

from pyplumio.const import ATTR_PASSWORD
from pyplumio.frames import FrameTypes, Response
from pyplumio.helpers.typing import DeviceDataType, MessageType
from pyplumio.structures.alerts import AlertsStructure
from pyplumio.structures.boiler_parameters import BoilerParametersStructure
from pyplumio.structures.data_schema import DataSchemaStructure
from pyplumio.structures.mixer_parameters import MixerParametersStructure
from pyplumio.structures.network_info import NetworkInfoStructure
from pyplumio.structures.product_info import ProductInfoStructure
from pyplumio.structures.program_version import ProgramVersionStructure
from pyplumio.structures.schedules import SchedulesStructure


class ProgramVersionResponse(Response):
    """Represents program version response. Contains software
    version info.
    """

    frame_type: ClassVar[int] = FrameTypes.RESPONSE_PROGRAM_VERSION

    def create_message(self, data: DeviceDataType) -> MessageType:
        """Create frame message."""
        return ProgramVersionStructure(self).encode(data)

    def decode_message(self, message: MessageType) -> DeviceDataType:
        """Decode frame message."""
        return ProgramVersionStructure(self).decode(message)[0]


class DeviceAvailableResponse(Response):
    """Represents device available response. Contains network
    information and status.
    """

    frame_type: ClassVar[int] = FrameTypes.RESPONSE_DEVICE_AVAILABLE

    def create_message(self, data: DeviceDataType) -> MessageType:
        """Create frame message."""
        return NetworkInfoStructure(self).encode(data)

    def decode_message(self, message: MessageType) -> DeviceDataType:
        """Decode frame message."""
        return NetworkInfoStructure(self).decode(message, offset=1)[0]


class UIDResponse(Response):
    """Represents UID response. Contains product and model info."""

    frame_type: ClassVar[int] = FrameTypes.RESPONSE_UID

    def create_message(self, data: DeviceDataType) -> MessageType:
        """Create frame message."""
        return ProductInfoStructure(self).encode(data)

    def decode_message(self, message: MessageType) -> DeviceDataType:
        """Decode frame message."""
        return ProductInfoStructure(self).decode(message, offset=3)[0]


class PasswordResponse(Response):
    """Represent password response. Contains device service password."""

    frame_type: ClassVar[int] = FrameTypes.RESPONSE_PASSWORD

    def decode_message(self, message: MessageType) -> DeviceDataType:
        """Decode frame message."""
        password = message[1:].decode() if message[1:] else None
        return {ATTR_PASSWORD: password}


class BoilerParametersResponse(Response):
    """Represents boiler parameters response. Contains editable boiler
    parameters.
    """

    frame_type: ClassVar[int] = FrameTypes.RESPONSE_BOILER_PARAMETERS

    def create_message(self, data: DeviceDataType) -> MessageType:
        """Create frame message."""
        return BoilerParametersStructure(self).encode(data)

    def decode_message(self, message: MessageType) -> DeviceDataType:
        """Decode frame message."""
        return BoilerParametersStructure(self).decode(message)[0]


class MixerParametersResponse(Response):
    """Represents mixer parameters response. Contains editable mixer
    parameters.
    """

    frame_type: ClassVar[int] = FrameTypes.RESPONSE_MIXER_PARAMETERS

    def decode_message(self, message: MessageType) -> DeviceDataType:
        """Decode frame message."""
        return MixerParametersStructure(self).decode(message)[0]


class DataSchemaResponse(Response):
    """Represents data schema response. Contains schema that describes
    regdata message structure.
    """

    frame_type: ClassVar[int] = FrameTypes.RESPONSE_DATA_SCHEMA

    def decode_message(self, message: MessageType) -> DeviceDataType:
        """Decode frame message."""
        return DataSchemaStructure(self).decode(message)[0]


class SetBoilerParameterResponse(Response):
    """Represents set boiler parameter response. Empty response
    that aknowledges, that boiler parameter was successfully changed.
    """

    frame_type: ClassVar[int] = FrameTypes.RESPONSE_SET_BOILER_PARAMETER


class SetMixerParameterResponse(Response):
    """Represents set mixer parameter response. Empty response
    that aknowledges, that mixer parameter was successfully changed.
    """

    frame_type: ClassVar[int] = FrameTypes.RESPONSE_SET_MIXER_PARAMETER


class BoilerControlResponse(Response):
    """Represents boiler control response. Empty response
    that aknowledges, that boiler control request was successfully
    processed.
    """

    frame_type: ClassVar[int] = FrameTypes.RESPONSE_BOILER_CONTROL


class AlertsResponse(Response):
    """Represents device alerts."""

    frame_type: ClassVar[int] = FrameTypes.RESPONSE_ALERTS

    def decode_message(self, message: MessageType) -> DeviceDataType:
        """Decode frame message."""
        return AlertsStructure(self).decode(message)[0]


class SchedulesResponse(Response):
    """Represents device schedule."""

    frame_type: ClassVar[int] = FrameTypes.RESPONSE_SCHEDULES

    def decode_message(self, message: MessageType) -> DeviceDataType:
        """Decode frame message."""
        return SchedulesStructure(self).decode(message)[0]
