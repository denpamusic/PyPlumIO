"""Contains message frame classes."""

from pyplumio import util
from pyplumio.constants import (
    DATA_FAN_POWER,
    DATA_FUEL_CONSUMPTION,
    DATA_FUEL_LEVEL,
    DATA_LOAD,
    DATA_MODE,
    DATA_POWER,
    DATA_THERMOSTAT,
    DATA_TRANSMISSION,
)
from pyplumio.data_types import Boolean
from pyplumio.exceptions import VersionError
from pyplumio.structures import (
    alarms,
    frame_versions,
    lambda_,
    mixers,
    modules,
    output_flags,
    outputs,
    statuses,
    temperatures,
    thermostats,
)

from . import Message


class RegData(Message):
    """Contains current regulator data.

    Attributes:
        frame_type -- frame type
    """

    frame_type: int = 0x08

    VERSION: str = "1.0"

    def __init__(self, *args, **kwargs):
        """Creates new RegData frame object.

        Keyword arguments:
            *args -- arguments for parent class init
            **kwargs -- keyword arguments for parent class init
        """
        super().__init__(*args, **kwargs)
        self.schema = []

    def parse_message(self, message: bytearray) -> None:
        """Parses RegData message into usable data.

        Keywords arguments:
            message -- message to parse
        """
        offset = 2
        frame_version = f"{message[offset+1]}.{message[offset]}"
        offset += 2
        self._data = {}
        if frame_version != self.VERSION:
            raise VersionError(f"Unknown regdata version: {int(frame_version)}")

        _, offset = frame_versions.from_bytes(message, offset, self._data)
        boolean_index = 0
        for param in self.schema:
            param_id, param_type = param
            if not isinstance(param_type, Boolean) and boolean_index > 0:
                offset += 1
                boolean_index = 0

            param_type.unpack(message[offset:])
            if isinstance(param_type, Boolean):
                boolean_index = param_type.index(boolean_index)

            self._data[param_id] = param_type.value
            offset += param_type.size


class CurrentData(Message):
    """Contains current device state data.

    Attributes:
        frame_type -- frame type
    """

    frame_type: int = 0x35

    def parse_message(self, message: bytearray) -> None:
        """Parses CurrentData message into usable data.

        Keywords arguments:
            message -- message to parse
        """
        self._data = {}
        offset = 0
        _, offset = frame_versions.from_bytes(message, offset, self._data)
        self._data[DATA_MODE] = message[offset]
        offset += 1
        _, offset = outputs.from_bytes(message, offset, self._data)
        _, offset = output_flags.from_bytes(message, offset, self._data)
        _, offset = temperatures.from_bytes(message, offset, self._data)
        _, offset = statuses.from_bytes(message, offset, self._data)
        _, offset = alarms.from_bytes(message, offset, self._data)
        self._data[DATA_FUEL_LEVEL] = message[offset]
        self._data[DATA_TRANSMISSION] = message[offset + 1]
        self._data[DATA_FAN_POWER] = util.unpack_float(
            message[offset + 2 : offset + 6]
        )[0]
        self._data[DATA_LOAD] = message[offset + 6]
        self._data[DATA_POWER] = util.unpack_float(message[offset + 7 : offset + 11])[0]
        self._data[DATA_FUEL_CONSUMPTION] = util.unpack_float(
            message[offset + 11 : offset + 15]
        )[0]
        self._data[DATA_THERMOSTAT] = message[offset + 15]
        offset += 16
        _, offset = modules.from_bytes(message, offset, self._data)
        _, offset = lambda_.from_bytes(message, offset, self._data)
        _, offset = thermostats.from_bytes(message, offset, self._data)
        _, offset = mixers.from_bytes(message, offset, self._data)
