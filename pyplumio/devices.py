"""Contains classes for supported devices."""
from __future__ import annotations

from abc import abstractmethod
from collections.abc import Iterable
import time
from typing import Any, Dict, Final, List, Optional, Tuple, Type, Union

from .constants import (
    DATA_FUEL_CONSUMPTION,
    DATA_MIXERS,
    DATA_MODE,
    DATA_MODULES,
    DATA_PASSWORD,
    DATA_PRODUCT,
    DATA_REGDATA,
    DATA_SCHEMA,
    DATA_UNKNOWN,
    ECOMAX_ADDRESS,
    ECOSTER_ADDRESS,
)
from .data_types import Boolean
from .frames import Frame, Request, Response, messages, requests, responses
from .helpers.base_device import BaseDevice
from .helpers.parameter import Parameter
from .helpers.product_info import ConnectedModules, ProductInfo
from .mixers import MixerCollection
from .storage import FrameBucket
from .structures.device_parameters import DEVICE_PARAMETERS, PARAMETER_BOILER_CONTROL
from .structures.frame_versions import FRAME_VERSIONS

MODE_OFF: Final = 0
MODE_FANNING: Final = 1
MODE_KINDLING: Final = 2
MODE_HEATING: Final = 3
MODE_SUSTAIN: Final = 4
MODE_IDLE: Final = 5
MODE_STANDBY: Final = 6
MODES: Final = (
    "Off",
    "Fanning",
    "Kindling",
    "Heating",
    "Sustain",
    "Idle",
    "Standby",
)


class Device(BaseDevice):
    """Device representation.

    Attributes:
        bucket -- frame version info storage
    """

    bucket: FrameBucket

    def __init__(
        self,
        data: Optional[Dict[str, Any]] = None,
        parameters: Optional[Dict[str, List[int]]] = None,
    ):
        """Creates device instance.

        Keyword arguments:
            data -- device data
            parameters -- editable parameters
        """
        self.bucket = FrameBucket(address=self.address, required=self.required_requests)
        super().__init__(data, parameters)

    def set_data(self, data: Dict[str, Any]) -> None:
        """Sets device data.

        Keyword arguments:
            data -- immutable device attributes
        """
        self._data = {**self._data, **data}
        if FRAME_VERSIONS in data:
            self.bucket.fill(data[FRAME_VERSIONS])

    def set_parameters(self, parameters: Dict[str, List[int]]) -> None:
        """Sets device parameters.

        Keyword arguments:
            parameters -- device changeable parameters
        """
        self._parameters = {
            name: Parameter(name, *parameter)
            for name, parameter in parameters.items()
            if name in self.parameter_keys
        }

    def handle_frame(self, frame: Frame) -> None:
        """Handles received frame.

        Keyword arguments:
            frame -- received frame
        """
        if self.data_responses is not None and isinstance(frame, self.data_responses):
            self.set_data(frame.data)

        elif self.parameter_responses is not None and isinstance(
            frame, self.parameter_responses
        ):
            self.set_parameters(frame.data)

    @property
    def product(self) -> ProductInfo:
        """Returns product info."""
        if DATA_PRODUCT not in self._data:
            self._data[DATA_PRODUCT] = ProductInfo()

        return self._data[DATA_PRODUCT]

    @property
    def modules(self) -> ConnectedModules:
        """Returns list of connected modules."""
        if DATA_MODULES not in self._data:
            self._data[DATA_MODULES] = ConnectedModules()

        return self._data[DATA_MODULES]

    @property
    def is_on(self) -> bool:
        """Returns current state."""
        if DATA_MODE not in self._data:
            self._data[DATA_MODE] = MODE_OFF

        return self._data[DATA_MODE] != MODE_OFF

    @property
    def mode(self) -> Optional[str]:
        """Returns current mode."""
        if DATA_MODE in self._data:
            if self._data[DATA_MODE] < len(MODES):
                return MODES[self._data[DATA_MODE]]

            return DATA_UNKNOWN

        return None

    @property
    def changes(self) -> List[Request]:
        """Returns changed device parameters."""
        changes = self.queue
        changes.extend(self.bucket.queue)
        return changes

    @property
    @abstractmethod
    def required_requests(self) -> Optional[Iterable[Type[Request]]]:
        """Returns a list of requests that will be queued to be sent
        when connection is established.
        """

    @property
    @abstractmethod
    def data_responses(
        self,
    ) -> Optional[Union[Tuple[Type[Response], ...], Type[Response]]]:
        """Returns a list of responses that contain data."""

    @property
    @abstractmethod
    def parameter_responses(
        self,
    ) -> Optional[Union[Tuple[Type[Response], ...], Type[Response]]]:
        """Returns a list of responses that contain parameters."""


class EcoMAX(Device):
    """ecoMAX device representation.

    Attributes:
        address -- device address
        mixers -- collection of device mixers
        _fuel_burned -- amount of fuel burned in kilograms
        _fuel_burned_timestamp -- timestamp of burned fuel value update
        _required_requests - requests to be queued on connection
        _data_responses - responses that contain data
        _parameter_responses - responses that contain parameters
    """

    address = ECOMAX_ADDRESS
    mixers: MixerCollection
    _fuel_burned: float = 0.0
    _fuel_burned_timestamp: float = 0.0
    _required_requests: Iterable[Type[Request]] = (
        requests.UID,
        requests.Password,
        requests.DataSchema,
        requests.BoilerParameters,
        requests.MixerParameters,
    )
    _data_responses: Tuple[Type[Response], ...] = (
        responses.UID,
        responses.Password,
        responses.DataSchema,
        messages.CurrentData,
        messages.RegData,
    )
    _parameter_responses: Type[Response] = responses.BoilerParameters

    def __init__(
        self,
        data: Optional[Dict[str, Any]] = None,
        parameters: Optional[Dict[str, List[int]]] = None,
    ):
        """Creates device instance.

        Keyword arguments:
            data -- device data
            parameters -- editable parameters
        """
        self.mixers = MixerCollection(address=self.address)
        self._fuel_burned = 0.0
        self._fuel_burned_timestamp = time.time()
        super().__init__(data, parameters)

    def __str__(self) -> str:
        """Converts device instance to a string."""
        return f"""
{super().__str__()}

Mixers:
{self.mixers}
""".strip()

    def set_data(self, data: Dict[str, Any]) -> None:
        """Sets device data.

        Keyword arguments:
            data -- immutable device attributes
        """
        if DATA_FUEL_CONSUMPTION in data:
            self._set_fuel_burned(data[DATA_FUEL_CONSUMPTION])

        if DATA_REGDATA in data and DATA_SCHEMA in self.data:
            self._set_data_from_regdata(data[DATA_REGDATA])

        if DATA_MODE in data:
            self._set_boiler_control_parameter(data[DATA_MODE])

        super().set_data(data)

    def handle_frame(self, frame: Frame) -> None:
        """Handles received frame.

        Keyword arguments:
            frame -- received frame
        """
        if isinstance(frame, messages.CurrentData):
            self.mixers.set_data(frame.data[DATA_MIXERS])

        elif isinstance(frame, responses.MixerParameters):
            self.mixers.set_parameters(frame.data[DATA_MIXERS])

        super().handle_frame(frame)

    def _set_data_from_regdata(self, regdata: bytes) -> None:
        """Extracts data from regdata message.

        Keyword arguments:
            regdata -- regdata message
        """
        offset = 0
        boolean_index = 0
        for param in self.data[DATA_SCHEMA]:
            param_id, param_type = param
            if not isinstance(param_type, Boolean) and boolean_index > 0:
                offset += 1
                boolean_index = 0

            param_type.unpack(regdata[offset:])
            if isinstance(param_type, Boolean):
                boolean_index = param_type.index(boolean_index)

            self._data[param_id] = param_type.value
            offset += param_type.size

    def _set_boiler_control_parameter(self, mode: int) -> None:
        """Sets boiler control parameter from device data.

        Keyword arguments:
            mode - current boiler mode
        """
        if PARAMETER_BOILER_CONTROL in self._parameters and isinstance(
            self._parameters[PARAMETER_BOILER_CONTROL], Parameter
        ):
            self._parameters[PARAMETER_BOILER_CONTROL].value = int(mode != MODE_OFF)
        else:
            self._parameters[PARAMETER_BOILER_CONTROL] = Parameter(
                name=PARAMETER_BOILER_CONTROL,
                value=int(mode != MODE_OFF),
                min_value=0,
                max_value=1,
            )

    def _set_fuel_burned(self, fuel_consumption: float) -> None:
        """Sets amount of fuel burned since last message.

        Keyword arguments:
            fuel_consumption -- fuel flow in kg/h
        """
        current_timestamp = time.time()
        seconds_passed = current_timestamp - self._fuel_burned_timestamp
        self._fuel_burned += (fuel_consumption / 3600) * seconds_passed
        self._fuel_burned_timestamp = current_timestamp

    @property
    def password(self) -> Optional[str]:
        """Returns device service password."""
        if DATA_PASSWORD in self._data:
            return self._data[DATA_PASSWORD]

        return None

    @property
    def fuel_burned(self) -> float:
        """Returns amount of fuel burned and resets counter."""
        fuel_burned = self._fuel_burned
        self._fuel_burned = 0.0
        return fuel_burned

    @property
    def changes(self) -> List[Request]:
        """Returns changed device parameters."""
        changes = super().changes
        changes.extend(self.mixers.queue)
        return changes

    @property
    def parameter_keys(self) -> List[str]:
        """Returns list of parameter keys."""
        parameters: List[str] = []
        parameters.extend(DEVICE_PARAMETERS)
        parameters.extend(PARAMETER_BOILER_CONTROL)
        return parameters

    @property
    def required_requests(self) -> Optional[Iterable[Type[Request]]]:
        """Returns a list of requests that will be queued to be sent
        when connection is established.
        """
        return self._required_requests

    @property
    def data_responses(
        self,
    ) -> Optional[Union[Tuple[Type[Response], ...], Type[Response]]]:
        """Returns a list of responses that contain data."""
        return self._data_responses

    @property
    def parameter_responses(
        self,
    ) -> Optional[Union[Tuple[Type[Response], ...], Type[Response]]]:
        """Returns a list of responses that contain parameters."""
        return self._parameter_responses


class EcoSTER(Device):
    """ecoSTER device representation.

    Attributes:
        address -- device address
    """

    address = ECOSTER_ADDRESS

    @property
    def parameter_keys(self) -> List[str]:
        """Returns list of parameter keys."""
        return []

    @property
    def required_requests(self) -> Optional[Iterable[Type[Request]]]:
        """Returns a list of requests that will be queued to be sent
        when connection is established.
        """
        return None

    @property
    def data_responses(
        self,
    ) -> Optional[Union[Tuple[Type[Response], ...], Type[Response]]]:
        """Returns a list of responses that contain data."""
        return None

    @property
    def parameter_responses(
        self,
    ) -> Optional[Union[Tuple[Type[Response], ...], Type[Response]]]:
        """Returns a list of responses that contain parameters."""
        return None


class DeviceCollection:
    """Collection of devices.

    Attributes:
        _classes -- device handler class names
        _addresses -- device classes mapped with device addresses
        _instances -- device handler instances
        _name -- device instances mapped with lowecased class names
    """

    def __init__(self):
        """Creates device collection."""
        self._classes = Device.__subclasses__()
        self._addresses = [v.address for v in self._classes]
        self._instances = {}
        self._names = {}

    def __getattr__(self, name: str) -> Optional[Device]:
        """Gets device by name.""

        Keyword arguments:
            name -- name of device to get
        """
        name = name.lower()
        if name in self._names:
            return self._instances[self._names[name]]

        raise AttributeError

    def __len__(self) -> int:
        """Returns number of devices in collection."""
        return len(self._instances)

    def has(self, needle) -> bool:
        """Checks if collection has device for specified address.

        Keyword arguments:
            needle -- address or name of device
        """
        return (needle in self._addresses) or (needle in self._names)

    def get(self, address: int) -> Optional[Device]:
        """Gets device by address.

        Keyword arguments:
            address -- address of device
        """
        if address not in self._instances:
            try:
                index = self._addresses.index(address)
                cls = self._classes[index]
            except ValueError:
                return None

            self._instances[address] = cls()
            self._names[cls.__name__.lower()] = address

        return self._instances[address]
