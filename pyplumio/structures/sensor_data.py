"""Contains sensor data decoder."""

from collections.abc import Generator, MutableMapping
from contextlib import suppress
from dataclasses import dataclass
import math
import struct
from typing import Any, Final

from typing_extensions import TypeVar

from pyplumio.const import ATTR_SCHEDULE, BYTE_UNDEFINED, DeviceState, LambdaState
from pyplumio.data_types import Float, UnsignedInt, UnsignedShort
from pyplumio.structures import StructureDecoder
from pyplumio.utils import ensure_dict

ATTR_AIR_IN_TEMP: Final = "air_in_temp"
ATTR_AIR_OUT_TEMP: Final = "air_out_temp"
ATTR_ALARM: Final = "alarm"
ATTR_BLOW_FAN1: Final = "blow_fan1"
ATTR_BLOW_FAN2: Final = "blow_fan2"
ATTR_BOILER_LOAD: Final = "boiler_load"
ATTR_BOILER_POWER: Final = "boiler_power"
ATTR_CIRCULATION_PUMP_FLAG: Final = "circulation_pump_flag"
ATTR_CIRCULATION_PUMP: Final = "circulation_pump"
ATTR_CONTACTS: Final = "contacts"
ATTR_CURRENT_TEMP: Final = "current_temp"
ATTR_ECOLAMBDA: Final = "ecolambda"
ATTR_ECOSTER: Final = "ecoster"
ATTR_EXCHANGER_TEMP: Final = "exchanger_temp"
ATTR_EXHAUST_TEMP: Final = "exhaust_temp"
ATTR_FAN_POWER: Final = "fan_power"
ATTR_FAN: Final = "fan"
ATTR_FAN2_EXHAUST: Final = "fan2_exhaust"
ATTR_FEEDER_TEMP: Final = "feeder_temp"
ATTR_FEEDER: Final = "feeder"
ATTR_FEEDER2: Final = "feeder2"
ATTR_FIREPLACE_PUMP: Final = "fireplace_pump"
ATTR_FIREPLACE_TEMP: Final = "fireplace_temp"
ATTR_FUEL_CONSUMPTION: Final = "fuel_consumption"
ATTR_FUEL_LEVEL: Final = "fuel_level"
ATTR_GCZ_CONTACT: Final = "gcz_contact"
ATTR_HEATING_PUMP_FLAG: Final = "heating_pump_flag"
ATTR_HEATING_PUMP: Final = "heating_pump"
ATTR_HEATING_STATUS: Final = "heating_status"
ATTR_HEATING_TARGET: Final = "heating_target"
ATTR_HEATING_TEMP: Final = "heating_temp"
ATTR_HYDRAULIC_COUPLER_TEMP: Final = "hydraulic_coupler_temp"
ATTR_LAMBDA_LEVEL: Final = "lambda_level"
ATTR_LAMBDA_STATE: Final = "lambda_state"
ATTR_LAMBDA_TARGET: Final = "lambda_target"
ATTR_LIGHTER: Final = "lighter"
ATTR_LOWER_BUFFER_TEMP: Final = "lower_buffer_temp"
ATTR_LOWER_SOLAR_TEMP: Final = "lower_solar_temp"
ATTR_MIXER_SENSORS: Final = "mixer_sensors"
ATTR_MIXERS_AVAILABLE: Final = "mixers_available"
ATTR_MIXERS_CONNECTED: Final = "mixers_connected"
ATTR_MODULE_A: Final = "module_a"
ATTR_MODULE_B: Final = "module_b"
ATTR_MODULE_C: Final = "module_c"
ATTR_MODULES: Final = "modules"
ATTR_OPTICAL_TEMP: Final = "optical_temp"
ATTR_OUTER_BOILER: Final = "outer_boiler"
ATTR_OUTER_FEEDER: Final = "outer_feeder"
ATTR_OUTSIDE_TEMP: Final = "outside_temp"
ATTR_PANEL: Final = "panel"
ATTR_PENDING_ALERTS: Final = "pending_alerts"
ATTR_PUMP: Final = "pump"
ATTR_RETURN_TEMP: Final = "return_temp"
ATTR_SOLAR_PUMP_FLAG: Final = "solar_pump_flag"
ATTR_SOLAR_PUMP: Final = "solar_pump"
ATTR_STATE: Final = "state"
ATTR_TARGET_TEMP: Final = "target_temp"
ATTR_THERMOSTAT_SENSORS: Final = "thermostat_sensors"
ATTR_THERMOSTAT: Final = "thermostat"
ATTR_THERMOSTATS_AVAILABLE: Final = "thermostats_available"
ATTR_THERMOSTATS_CONNECTED: Final = "thermostats_connected"
ATTR_TOTAL_GAIN: Final = "total_gain"
ATTR_TRANSMISSION: Final = "transmission"
ATTR_UPPER_BUFFER_TEMP: Final = "upper_buffer_temp"
ATTR_UPPER_SOLAR_TEMP: Final = "upper_solar_temp"
ATTR_WATER_HEATER_PUMP_FLAG: Final = "water_heater_pump_flag"
ATTR_WATER_HEATER_PUMP: Final = "water_heater_pump"
ATTR_WATER_HEATER_STATUS: Final = "water_heater_status"
ATTR_WATER_HEATER_TARGET: Final = "water_heater_target"
ATTR_WATER_HEATER_TEMP: Final = "water_heater_temp"

OUTPUTS: tuple[str, ...] = (
    ATTR_FAN,
    ATTR_FEEDER,
    ATTR_HEATING_PUMP,
    ATTR_WATER_HEATER_PUMP,
    ATTR_CIRCULATION_PUMP,
    ATTR_LIGHTER,
    ATTR_ALARM,
    ATTR_OUTER_BOILER,
    ATTR_FAN2_EXHAUST,
    ATTR_FEEDER2,
    ATTR_OUTER_FEEDER,
    ATTR_SOLAR_PUMP,
    ATTR_FIREPLACE_PUMP,
    ATTR_GCZ_CONTACT,
    ATTR_BLOW_FAN1,
    ATTR_BLOW_FAN2,
)

TEMPERATURES: tuple[str, ...] = (
    ATTR_HEATING_TEMP,
    ATTR_FEEDER_TEMP,
    ATTR_WATER_HEATER_TEMP,
    ATTR_OUTSIDE_TEMP,
    ATTR_RETURN_TEMP,
    ATTR_EXHAUST_TEMP,
    ATTR_OPTICAL_TEMP,
    ATTR_UPPER_BUFFER_TEMP,
    ATTR_LOWER_BUFFER_TEMP,
    ATTR_UPPER_SOLAR_TEMP,
    ATTR_LOWER_SOLAR_TEMP,
    ATTR_FIREPLACE_TEMP,
    ATTR_TOTAL_GAIN,
    ATTR_HYDRAULIC_COUPLER_TEMP,
    ATTR_EXCHANGER_TEMP,
    ATTR_AIR_IN_TEMP,
    ATTR_AIR_OUT_TEMP,
)

STATUSES: tuple[str, ...] = (
    ATTR_HEATING_TARGET,
    ATTR_HEATING_STATUS,
    ATTR_WATER_HEATER_TARGET,
    ATTR_WATER_HEATER_STATUS,
)

MODULES: tuple[str, ...] = (
    ATTR_MODULE_A,
    ATTR_MODULE_B,
    ATTR_MODULE_C,
    ATTR_ECOLAMBDA,
    ATTR_ECOSTER,
    ATTR_PANEL,
)

FUEL_LEVEL_OFFSET: Final = 101


@dataclass(slots=True)
class ConnectedModules:
    """Represents a firmware version info for connected module."""

    module_a: str | None = None
    module_b: str | None = None
    module_c: str | None = None
    ecolambda: str | None = None
    ecoster: str | None = None
    panel: str | None = None


struct_version = struct.Struct("<BBB")
struct_vendor = struct.Struct("<BB")

_DataT = TypeVar("_DataT", bound=MutableMapping)


class SensorDataStructure(StructureDecoder):
    """Represents a schedule data structure."""

    __slots__ = ("_offset",)

    _offset: int

    def _decode_outputs(self, message: bytearray, data: _DataT) -> _DataT:
        """Decode outputs from message."""
        outputs = UnsignedInt.from_bytes(message, self._offset)
        self._offset += outputs.size
        for index, output in enumerate(OUTPUTS):
            data[output] = bool(outputs.value & 2**index)

        return data

    def _decode_output_flags(self, message: bytearray, data: _DataT) -> _DataT:
        """Decode output flags from message."""
        output_flags = UnsignedInt.from_bytes(message, self._offset)
        self._offset += output_flags.size
        data[ATTR_HEATING_PUMP_FLAG] = bool(output_flags.value & 0x04)
        data[ATTR_WATER_HEATER_PUMP_FLAG] = bool(output_flags.value & 0x08)
        data[ATTR_CIRCULATION_PUMP_FLAG] = bool(output_flags.value & 0x10)
        data[ATTR_SOLAR_PUMP_FLAG] = bool(output_flags.value & 0x800)
        return data

    def _decode_temperatures(self, message: bytearray, data: _DataT) -> _DataT:
        """Decode temperatures from message."""
        offset = self._offset
        temperatures = message[offset]
        offset += 1
        for _ in range(temperatures):
            index = message[offset]
            offset += 1
            temp = Float.from_bytes(message, offset)
            offset += temp.size
            if (not math.isnan(temp.value)) and 0 <= index < len(TEMPERATURES):
                # Temperature exists and index is in the correct range.
                data[TEMPERATURES[index]] = temp.value

        self._offset = offset
        return data

    def _decode_statuses(self, message: bytearray, data: _DataT) -> _DataT:
        """Decode statuses from message."""
        for index, status in enumerate(STATUSES):
            data[status] = message[self._offset + index]

        self._offset += len(STATUSES)
        return data

    def _decode_pending_alerts(self, message: bytearray, data: _DataT) -> _DataT:
        """Decode pending alerts from message."""
        pending_alerts = message[self._offset]
        data[ATTR_PENDING_ALERTS] = pending_alerts
        self._offset += pending_alerts + 1
        return data

    def _decode_fuel_level(self, message: bytearray, data: _DataT) -> _DataT:
        """Decode fuel level from message."""
        fuel_level = message[self._offset]
        self._offset += 1
        if fuel_level != BYTE_UNDEFINED:
            # Fuel offset requirement on at least ecoMAX 860P6-O.
            # See: https://github.com/denpamusic/PyPlumIO/issues/19
            data[ATTR_FUEL_LEVEL] = (
                fuel_level
                if fuel_level < FUEL_LEVEL_OFFSET
                else fuel_level - FUEL_LEVEL_OFFSET
            )

        return data

    def _decode_boiler_load(self, message: bytearray, data: _DataT) -> _DataT:
        """Decode boiler load from message."""
        boiler_load = message[self._offset]
        self._offset += 1
        if boiler_load != BYTE_UNDEFINED:
            data[ATTR_BOILER_LOAD] = boiler_load

        return data

    def _decode_float_value(
        self, name: str, message: bytearray, data: _DataT
    ) -> _DataT:
        """Decode float value and increase an offset."""
        float_value = Float.from_bytes(message, self._offset)
        self._offset += float_value.size
        if not math.isnan(float_value.value):
            data[name] = float_value.value

        return data

    def _decode_modules(self, message: bytearray, data: _DataT) -> _DataT:
        """Decode modules from message."""
        offset = self._offset

        def _unpack_module_version() -> Generator[tuple[str, str | None]]:
            """Unpack a module version."""
            nonlocal offset
            for module in MODULES:
                if message[offset] != BYTE_UNDEFINED:
                    version_data = struct_version.unpack_from(message, offset)
                    version = ".".join(str(i) for i in version_data)
                    offset += struct_version.size
                    if module == ATTR_MODULE_A:
                        vendor_code, vendor_version = struct_vendor.unpack_from(
                            message, offset
                        )
                        version += f".{chr(vendor_code) + str(vendor_version)}"
                        offset += struct_vendor.size
                else:
                    offset += 1
                    version = None

                yield module, version

        data[ATTR_MODULES] = ConnectedModules(**dict(_unpack_module_version()))
        self._offset = offset
        return data

    def _decode_lambda_sensor(self, message: bytearray, data: _DataT) -> _DataT:
        """Decode lambda sensor from message."""
        offset = self._offset
        lambda_state = message[offset]
        offset += 1
        if lambda_state != BYTE_UNDEFINED:
            lambda_target = message[offset]
            offset += 1
            level = UnsignedShort.from_bytes(message, offset)
            offset += level.size
            with suppress(ValueError):
                lambda_state = LambdaState(lambda_state)

            data[ATTR_LAMBDA_STATE] = lambda_state
            data[ATTR_LAMBDA_TARGET] = lambda_target
            data[ATTR_LAMBDA_LEVEL] = level.value / 10

        self._offset = offset
        return data

    def _decode_thermostat_sensors(self, message: bytearray, data: _DataT) -> _DataT:
        """Decode thermostat sensors from message."""
        contact_mask = 1
        schedule_mask = 1 << 3
        offset = self._offset

        def _unpack_thermostat_sensors(contacts: int) -> dict[str, Any] | None:
            """Unpack sensors for a single thermostat."""
            nonlocal offset, contact_mask, schedule_mask
            state = message[offset]
            offset += 1
            current_temp = Float.from_bytes(message, offset)
            offset += current_temp.size
            target_temp = Float.from_bytes(message, offset)
            offset += target_temp.size
            contacts_state = bool(contacts & contact_mask)
            contact_mask <<= 1
            schedule_state = bool(contacts & schedule_mask)
            schedule_mask <<= 1

            if math.isnan(current_temp.value) or target_temp.value <= 0:
                return None

            return {
                ATTR_STATE: state,
                ATTR_CURRENT_TEMP: current_temp.value,
                ATTR_TARGET_TEMP: target_temp.value,
                ATTR_CONTACTS: contacts_state,
                ATTR_SCHEDULE: schedule_state,
            }

        def _thermostat_sensors(contacts: int) -> Generator[tuple[int, dict[str, Any]]]:
            """Get thermostat sensors."""
            for index in range(thermostats):
                if sensors := _unpack_thermostat_sensors(contacts):
                    yield (index, sensors)

        contacts = message[offset]
        offset += 1
        if contacts != BYTE_UNDEFINED:
            thermostats = message[offset]
            offset += 1
            thermostat_sensors = dict(_thermostat_sensors(contacts))
            data[ATTR_THERMOSTAT_SENSORS] = thermostat_sensors
            data[ATTR_THERMOSTATS_CONNECTED] = len(thermostat_sensors)
            data[ATTR_THERMOSTATS_AVAILABLE] = thermostats

        self._offset = offset
        return data

    def _decode_mixer_sensors(self, message: bytearray, data: _DataT) -> _DataT:
        """Decode mixer sensors from message."""
        offset = self._offset

        def _unpack_mixer_sensors() -> dict[str, Any] | None:
            """Unpack sensors for a single mixer."""
            nonlocal offset
            current_temp = Float.from_bytes(message, offset)
            offset += current_temp.size
            data = None
            if not math.isnan(current_temp.value):
                data = {
                    ATTR_CURRENT_TEMP: current_temp.value,
                    ATTR_TARGET_TEMP: message[offset],
                    ATTR_PUMP: bool(message[offset + 2] & 0x01),
                }

            offset += 4
            return data

        def _mixer_sensors(mixers: int) -> Generator[tuple[int, dict[str, Any]]]:
            """Get mixer sensors."""
            for index in range(mixers):
                if sensors := _unpack_mixer_sensors():
                    yield (index, sensors)

        mixers = message[offset]
        offset += 1
        mixer_sensors = dict(_mixer_sensors(mixers))
        data[ATTR_MIXER_SENSORS] = mixer_sensors
        data[ATTR_MIXERS_CONNECTED] = len(mixer_sensors)
        data[ATTR_MIXERS_AVAILABLE] = mixers
        self._offset = offset
        return data

    def decode(
        self, message: bytearray, offset: int = 0, data: dict[str, Any] | None = None
    ) -> tuple[dict[str, Any], int]:
        """Decode bytes and return message data and offset."""
        data = ensure_dict(data)
        data[ATTR_STATE] = message[offset]
        self._offset = offset + 1
        with suppress(ValueError):
            data[ATTR_STATE] = DeviceState(data[ATTR_STATE])

        data = self._decode_outputs(message, data)
        data = self._decode_output_flags(message, data)
        data = self._decode_temperatures(message, data)
        data = self._decode_statuses(message, data)
        data = self._decode_pending_alerts(message, data)
        data = self._decode_fuel_level(message, data)
        data[ATTR_TRANSMISSION] = message[self._offset]
        self._offset += 1
        data = self._decode_float_value(ATTR_FAN_POWER, message, data)
        data = self._decode_boiler_load(message, data)
        data = self._decode_float_value(ATTR_BOILER_POWER, message, data)
        data = self._decode_float_value(ATTR_FUEL_CONSUMPTION, message, data)
        data[ATTR_THERMOSTAT] = message[self._offset]
        self._offset += 1
        data = self._decode_modules(message, data)
        data = self._decode_lambda_sensor(message, data)
        data = self._decode_thermostat_sensors(message, data)
        data = self._decode_mixer_sensors(message, data)
        return data, offset


__all__ = [
    "ATTR_AIR_IN_TEMP",
    "ATTR_AIR_OUT_TEMP",
    "ATTR_ALARM",
    "ATTR_BLOW_FAN1",
    "ATTR_BLOW_FAN2",
    "ATTR_BOILER_LOAD",
    "ATTR_BOILER_POWER",
    "ATTR_CIRCULATION_PUMP",
    "ATTR_CIRCULATION_PUMP_FLAG",
    "ATTR_CONTACTS",
    "ATTR_CURRENT_TEMP",
    "ATTR_ECOLAMBDA",
    "ATTR_ECOSTER",
    "ATTR_EXCHANGER_TEMP",
    "ATTR_EXHAUST_TEMP",
    "ATTR_FAN",
    "ATTR_FAN2_EXHAUST",
    "ATTR_FAN_POWER",
    "ATTR_FEEDER",
    "ATTR_FEEDER2",
    "ATTR_FEEDER_TEMP",
    "ATTR_FIREPLACE_PUMP",
    "ATTR_FIREPLACE_TEMP",
    "ATTR_FUEL_CONSUMPTION",
    "ATTR_FUEL_LEVEL",
    "ATTR_GCZ_CONTACT",
    "ATTR_HEATING_PUMP",
    "ATTR_HEATING_PUMP_FLAG",
    "ATTR_HEATING_STATUS",
    "ATTR_HEATING_TARGET",
    "ATTR_HEATING_TEMP",
    "ATTR_HYDRAULIC_COUPLER_TEMP",
    "ATTR_LAMBDA_LEVEL",
    "ATTR_LAMBDA_STATE",
    "ATTR_LAMBDA_TARGET",
    "ATTR_LIGHTER",
    "ATTR_LOWER_BUFFER_TEMP",
    "ATTR_LOWER_SOLAR_TEMP",
    "ATTR_MIXER_SENSORS",
    "ATTR_MIXERS_AVAILABLE",
    "ATTR_MIXERS_CONNECTED",
    "ATTR_MODULE_A",
    "ATTR_MODULE_B",
    "ATTR_MODULE_C",
    "ATTR_MODULES",
    "ATTR_OPTICAL_TEMP",
    "ATTR_OUTER_BOILER",
    "ATTR_OUTER_FEEDER",
    "ATTR_OUTSIDE_TEMP",
    "ATTR_PANEL",
    "ATTR_PENDING_ALERTS",
    "ATTR_PUMP",
    "ATTR_RETURN_TEMP",
    "ATTR_SOLAR_PUMP",
    "ATTR_SOLAR_PUMP_FLAG",
    "ATTR_STATE",
    "ATTR_TARGET_TEMP",
    "ATTR_THERMOSTAT",
    "ATTR_THERMOSTAT_SENSORS",
    "ATTR_THERMOSTATS_AVAILABLE",
    "ATTR_THERMOSTATS_CONNECTED",
    "ATTR_TOTAL_GAIN",
    "ATTR_TRANSMISSION",
    "ATTR_UPPER_BUFFER_TEMP",
    "ATTR_UPPER_SOLAR_TEMP",
    "ATTR_WATER_HEATER_PUMP",
    "ATTR_WATER_HEATER_PUMP_FLAG",
    "ATTR_WATER_HEATER_STATUS",
    "ATTR_WATER_HEATER_TARGET",
    "ATTR_WATER_HEATER_TEMP",
    "ConnectedModules",
    "MODULES",
    "OUTPUTS",
    "SensorDataStructure",
    "STATUSES",
    "TEMPERATURES",
]
