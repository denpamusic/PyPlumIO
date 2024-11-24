"""Contains regulator parameter structure decoder."""

from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING, Any, Final

from dataslots import dataslots

from pyplumio.const import (
    ATTR_INDEX,
    ATTR_OFFSET,
    ATTR_SIZE,
    ATTR_VALUE,
    PERCENTAGE,
    FrameType,
    ProductType,
    UnitOfMeasurement,
)
from pyplumio.frames import Request
from pyplumio.helpers.parameter import (
    Number,
    NumberDescription,
    Parameter,
    ParameterDescription,
    ParameterValues,
    Switch,
    SwitchDescription,
    unpack_parameter,
)
from pyplumio.structures import StructureDecoder
from pyplumio.structures.thermostat_parameters import ATTR_THERMOSTAT_PROFILE
from pyplumio.utils import ensure_dict

if TYPE_CHECKING:
    from pyplumio.devices.ecomax import EcoMAX

ATTR_ECOMAX_CONTROL: Final = "ecomax_control"
ATTR_ECOMAX_PARAMETERS: Final = "ecomax_parameters"

ECOMAX_PARAMETER_SIZE: Final = 3


@dataclass
class EcomaxParameterDescription(ParameterDescription):
    """Represents an ecoMAX parameter description."""

    __slots__ = ()


class EcomaxParameter(Parameter):
    """Represents an ecoMAX parameter."""

    __slots__ = ()

    device: EcoMAX
    description: EcomaxParameterDescription

    async def create_request(self) -> Request:
        """Create a request to change the parameter."""
        handler = partial(Request.create, recipient=self.device.address)
        if self.description.name == ATTR_ECOMAX_CONTROL:
            return await handler(
                frame_type=FrameType.REQUEST_ECOMAX_CONTROL,
                data={ATTR_VALUE: self.values.value},
            )

        if self.description.name == ATTR_THERMOSTAT_PROFILE:
            return await handler(
                frame_type=FrameType.REQUEST_SET_THERMOSTAT_PARAMETER,
                data={
                    ATTR_INDEX: self._index,
                    ATTR_VALUE: self.values.value,
                    ATTR_OFFSET: 0,
                    ATTR_SIZE: 1,
                },
            )

        return await handler(
            frame_type=FrameType.REQUEST_SET_ECOMAX_PARAMETER,
            data={ATTR_INDEX: self._index, ATTR_VALUE: self.values.value},
        )

    async def create_refresh_request(self) -> Request:
        """Create a request to refresh the parameter."""
        return await Request.create(
            FrameType.REQUEST_ECOMAX_PARAMETERS, recipient=self.device.address
        )

    @property
    def is_tracking_changes(self) -> bool:
        """Return True if remote is tracking changes, False otherwise."""
        return self.device.has_frame_version(FrameType.REQUEST_ECOMAX_PARAMETERS)


@dataslots
@dataclass
class EcomaxNumberDescription(EcomaxParameterDescription, NumberDescription):
    """Represents an ecoMAX number description."""

    multiplier: float = 1.0
    offset: int = 0
    precision: int = 6


class EcomaxNumber(EcomaxParameter, Number):
    """Represents a ecoMAX number."""

    __slots__ = ()

    description: EcomaxNumberDescription

    async def set(
        self, value: float | int, retries: int = 5, timeout: float = 5.0
    ) -> bool:
        """Set a parameter value."""
        value += self.description.offset
        value = round(value / self.description.multiplier, self.description.precision)
        return await super().set(value, retries, timeout)

    @property
    def value(self) -> float:
        """Return the value."""
        value = self.values.value - self.description.offset
        return round(value * self.description.multiplier, self.description.precision)

    @property
    def min_value(self) -> float:
        """Return the minimum allowed value."""
        value = self.values.min_value - self.description.offset
        return round(value * self.description.multiplier, self.description.precision)

    @property
    def max_value(self) -> float:
        """Return the maximum allowed value."""
        value = self.values.max_value - self.description.offset
        return round(value * self.description.multiplier, self.description.precision)


@dataslots
@dataclass
class EcomaxSwitchDescription(EcomaxParameterDescription, SwitchDescription):
    """Represents an ecoMAX switch description."""


class EcomaxSwitch(EcomaxParameter, Switch):
    """Represents an ecoMAX switch."""

    __slots__ = ()

    description: EcomaxSwitchDescription


ECOMAX_PARAMETERS: dict[ProductType, tuple[EcomaxParameterDescription, ...]] = {
    ProductType.ECOMAX_P: (
        EcomaxNumberDescription(
            name="airflow_power_100",
            unit_of_measurement=PERCENTAGE,
        ),
        EcomaxNumberDescription(
            name="airflow_power_50",
            unit_of_measurement=PERCENTAGE,
        ),
        EcomaxNumberDescription(
            name="airflow_power_30",
            unit_of_measurement=PERCENTAGE,
        ),
        EcomaxNumberDescription(
            name="boiler_power_100",
            unit_of_measurement=UnitOfMeasurement.KILO_WATT,
        ),
        EcomaxNumberDescription(
            name="boiler_power_50",
            unit_of_measurement=UnitOfMeasurement.KILO_WATT,
        ),
        EcomaxNumberDescription(
            name="boiler_power_30",
            unit_of_measurement=UnitOfMeasurement.KILO_WATT,
        ),
        EcomaxNumberDescription(
            name="max_fan_boiler_power",
            unit_of_measurement=PERCENTAGE,
        ),
        EcomaxNumberDescription(
            name="min_fan_boiler_power",
            unit_of_measurement=PERCENTAGE,
        ),
        EcomaxNumberDescription(
            name="fuel_feeding_work_100",
            unit_of_measurement=UnitOfMeasurement.SECONDS,
        ),
        EcomaxNumberDescription(
            name="fuel_feeding_work_50",
            unit_of_measurement=UnitOfMeasurement.SECONDS,
        ),
        EcomaxNumberDescription(
            name="fuel_feeding_work_30",
            unit_of_measurement=UnitOfMeasurement.SECONDS,
        ),
        EcomaxNumberDescription(
            name="fuel_feeding_pause_100",
            unit_of_measurement=UnitOfMeasurement.SECONDS,
        ),
        EcomaxNumberDescription(
            name="fuel_feeding_pause_50",
            unit_of_measurement=UnitOfMeasurement.SECONDS,
        ),
        EcomaxNumberDescription(
            name="fuel_feeding_pause_30",
            unit_of_measurement=UnitOfMeasurement.SECONDS,
        ),
        EcomaxNumberDescription(
            name="cycle_duration",
            unit_of_measurement=UnitOfMeasurement.SECONDS,
        ),
        EcomaxNumberDescription(
            name="h2_hysteresis",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="h1_hysteresis",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="heating_hysteresis",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxSwitchDescription(
            name="fuzzy_logic",
        ),
        EcomaxNumberDescription(
            name="min_fuzzy_logic_power",
            unit_of_measurement=PERCENTAGE,
        ),
        EcomaxNumberDescription(
            name="max_fuzzy_logic_power",
            unit_of_measurement=PERCENTAGE,
        ),
        EcomaxNumberDescription(
            name="min_boiler_power",
            unit_of_measurement=UnitOfMeasurement.KILO_WATT,
        ),
        EcomaxNumberDescription(
            name="max_boiler_power",
            unit_of_measurement=UnitOfMeasurement.KILO_WATT,
        ),
        EcomaxNumberDescription(
            name="min_fan_power",
            unit_of_measurement=PERCENTAGE,
        ),
        EcomaxNumberDescription(
            name="max_fan_power",
            unit_of_measurement=PERCENTAGE,
        ),
        EcomaxNumberDescription(
            name="reduction_airflow_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="fan_power_gain",
            unit_of_measurement=PERCENTAGE,
        ),
        EcomaxNumberDescription(
            name="fuzzy_logic_fuel_flow_correction",
            unit_of_measurement=PERCENTAGE,
        ),
        EcomaxNumberDescription(
            name="fuel_flow_correction",
            unit_of_measurement=PERCENTAGE,
        ),
        EcomaxNumberDescription(
            name="airflow_correction_100",
            unit_of_measurement=PERCENTAGE,
        ),
        EcomaxNumberDescription(
            name="feeder_correction_100",
            unit_of_measurement=PERCENTAGE,
        ),
        EcomaxNumberDescription(
            name="airflow_correction_50",
            unit_of_measurement=PERCENTAGE,
        ),
        EcomaxNumberDescription(
            name="feeder_correction_50",
            unit_of_measurement=PERCENTAGE,
        ),
        EcomaxNumberDescription(
            name="airflow_correction_30",
            unit_of_measurement=PERCENTAGE,
        ),
        EcomaxNumberDescription(
            name="feeder_correction_30",
            unit_of_measurement=PERCENTAGE,
        ),
        EcomaxNumberDescription(
            name="grate_airflow_power",
            unit_of_measurement=PERCENTAGE,
        ),
        EcomaxNumberDescription(
            name="grate_heating_hysteresis",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="grate_fan_work",
            unit_of_measurement=UnitOfMeasurement.SECONDS,
        ),
        EcomaxNumberDescription(
            name="grate_fan_pause",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        EcomaxNumberDescription(
            name="grate_heating_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="grate_fuel_detection_time",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        EcomaxNumberDescription(
            name="kindling_airflow_power",
            unit_of_measurement=PERCENTAGE,
        ),
        EcomaxNumberDescription(
            name="kindling_low_airflow_power",
            unit_of_measurement=PERCENTAGE,
        ),
        EcomaxNumberDescription(
            name="kindling_airflow_delay",
            unit_of_measurement=UnitOfMeasurement.SECONDS,
        ),
        EcomaxNumberDescription(
            name="kindling_test_time",
            unit_of_measurement=UnitOfMeasurement.SECONDS,
        ),
        EcomaxNumberDescription(
            name="kindling_feeder_work",
        ),
        EcomaxNumberDescription(
            name="kindling_feeder_dose",
            unit_of_measurement=UnitOfMeasurement.GRAMS,
        ),
        EcomaxNumberDescription(
            name="kindling_time",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        EcomaxNumberDescription(
            name="warming_up_time",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        EcomaxNumberDescription(
            name="kindling_finish_exhaust_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="kindling_finish_threshold_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="kindling_fumes_delta_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="kindling_delta_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="kindling_min_power_time",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        EcomaxNumberDescription(
            name="stabilization_time",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        EcomaxNumberDescription(
            name="stabilization_airflow_power",
            unit_of_measurement=PERCENTAGE,
        ),
        EcomaxNumberDescription(
            name="supervision_time",
        ),
        EcomaxNumberDescription(
            name="supervision_feeder_work",
            unit_of_measurement=UnitOfMeasurement.SECONDS,
        ),
        EcomaxNumberDescription(
            name="supervision_feeder_dose",
            unit_of_measurement=UnitOfMeasurement.GRAMS,
        ),
        EcomaxNumberDescription(
            name="supervision_feeder_pause",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        EcomaxNumberDescription(
            name="supervision_cycle_duration",
            unit_of_measurement=UnitOfMeasurement.SECONDS,
        ),
        EcomaxNumberDescription(
            name="supervision_airflow_power",
            unit_of_measurement=PERCENTAGE,
        ),
        EcomaxNumberDescription(
            name="supervision_fan_pause",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        EcomaxNumberDescription(
            name="supervision_fan_work",
            unit_of_measurement=UnitOfMeasurement.SECONDS,
        ),
        EcomaxNumberDescription(
            name="increase_fan_support_mode",
        ),
        EcomaxNumberDescription(
            name="burning_off_max_time",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        EcomaxNumberDescription(
            name="burning_off_min_time",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        EcomaxNumberDescription(
            name="burning_off_time",
        ),
        EcomaxNumberDescription(
            name="burning_off_airflow_power",
            unit_of_measurement=PERCENTAGE,
        ),
        EcomaxNumberDescription(
            name="burning_off_fan_work",
        ),
        EcomaxNumberDescription(
            name="burning_off_fan_pause",
        ),
        EcomaxNumberDescription(
            name="start_burning_off",
            unit_of_measurement=PERCENTAGE,
        ),
        EcomaxNumberDescription(
            name="stop_burning_off",
            unit_of_measurement=PERCENTAGE,
        ),
        EcomaxNumberDescription(
            name="cleaning_begin_time",
        ),
        EcomaxNumberDescription(
            name="burning_off_cleaning_time",
        ),
        EcomaxNumberDescription(
            name="cleaning_airflow_power",
            unit_of_measurement=PERCENTAGE,
        ),
        EcomaxNumberDescription(
            name="warming_up_pause_time",
        ),
        EcomaxNumberDescription(
            name="warming_up_cycle_time",
        ),
        EcomaxNumberDescription(
            name="remind_time",
        ),
        EcomaxSwitchDescription(
            name="lambda_control",
        ),
        EcomaxNumberDescription(
            name="lambda_correction_range",
        ),
        EcomaxNumberDescription(
            name="oxygen_100",
        ),
        EcomaxNumberDescription(
            name="oxygen_50",
        ),
        EcomaxNumberDescription(
            name="oxygen_30",
        ),
        EcomaxNumberDescription(
            name="fuzzy_logic_oxygen_correction",
        ),
        EcomaxNumberDescription(
            name="max_fuel_flow",
            multiplier=0.1,
            unit_of_measurement=UnitOfMeasurement.KILOGRAMS_PER_HOUR,
        ),
        EcomaxNumberDescription(
            name="feeder_calibration",
        ),
        EcomaxNumberDescription(
            name="fuel_factor",
        ),
        EcomaxNumberDescription(
            name="fuel_calorific_value",
            multiplier=0.1,
            unit_of_measurement=UnitOfMeasurement.KILO_WATT_HOUR_PER_KILOGRAM,
        ),
        EcomaxNumberDescription(
            name="fuel_detection_time",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        EcomaxNumberDescription(
            name="fuel_detection_exhaust_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxSwitchDescription(
            name="schedule_feeder_2",
        ),
        EcomaxNumberDescription(
            name="feed2_h1",
        ),
        EcomaxNumberDescription(
            name="feed2_h2",
        ),
        EcomaxNumberDescription(
            name="feed2_h3",
        ),
        EcomaxNumberDescription(
            name="feed2_h4",
        ),
        EcomaxNumberDescription(
            name="feed2_work",
        ),
        EcomaxNumberDescription(
            name="feed2_pause",
        ),
        EcomaxNumberDescription(
            name="heating_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="min_heating_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="max_heating_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="heating_pump_enable_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="pause_heating_for_water_heater",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        EcomaxNumberDescription(
            name="thermostat_pause",
        ),
        EcomaxNumberDescription(
            name="thermostat_work",
        ),
        EcomaxNumberDescription(
            name="increase_heating_temp_for_water_heater",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxSwitchDescription(
            name="weather_control",
        ),
        EcomaxNumberDescription(
            name="heating_curve",
            multiplier=0.1,
        ),
        EcomaxNumberDescription(
            name="heating_curve_shift",
            offset=20,
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="weather_factor",
        ),
        EcomaxNumberDescription(
            name="thermostat_operation",
        ),
        EcomaxSwitchDescription(
            name="thermostat_mode",
        ),
        EcomaxNumberDescription(
            name="thermostat_decrease_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxSwitchDescription(
            name="disable_pump_on_thermostat",
        ),
        EcomaxNumberDescription(
            name="boiler_alert_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="max_feeder_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="external_boiler_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="alert_notify",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="pump_hysteresis",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="water_heater_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="min_water_heater_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="max_water_heater_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="water_heater_work_mode",
        ),
        EcomaxNumberDescription(
            name="water_heater_hysteresis",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxSwitchDescription(
            name="water_heater_disinfection",
        ),
        EcomaxNumberDescription(
            name="summer_mode",
        ),
        EcomaxNumberDescription(
            name="summer_mode_enable_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="summer_mode_disable_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="water_heater_work_extension",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        EcomaxSwitchDescription(
            name="circulation_control",
        ),
        EcomaxNumberDescription(
            name="circulation_pause",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        EcomaxNumberDescription(
            name="circulation_work",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        EcomaxNumberDescription(
            name="circulation_start_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxSwitchDescription(
            name="buffer_control",
        ),
        EcomaxNumberDescription(
            name="max_buffer_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="min_buffer_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="buffer_hysteresis",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="buffer_load_start",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="buffer_load_stop",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
    ),
    ProductType.ECOMAX_I: (
        EcomaxNumberDescription(
            name="water_heater_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxSwitchDescription(
            name="water_heater_priority",
        ),
        EcomaxNumberDescription(
            name="water_heater_support",
        ),
        EcomaxNumberDescription(
            name="min_water_heater_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="max_water_heater_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="water_heater_work_extension",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        EcomaxNumberDescription(
            name="water_heater_hysteresis",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxSwitchDescription(
            name="water_heater_disinfection",
        ),
        EcomaxNumberDescription(
            name="water_heater_work_mode",
        ),
        EcomaxSwitchDescription(
            name="solar_support",
        ),
        EcomaxNumberDescription(
            name="solar_pump_on_delta_temp",
            multiplier=0.1,
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="solar_pump_off_delta_temp",
            multiplier=0.1,
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="min_collector_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="max_collector_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="collector_off_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="min_pump_revolutions",
        ),
        EcomaxNumberDescription(
            name="solar_antifreeze",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxSwitchDescription(
            name="circulation_control",
        ),
        EcomaxNumberDescription(
            name="circulation_pause",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        EcomaxNumberDescription(
            name="circulation_work",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        EcomaxNumberDescription(
            name="circulation_start_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="main_heat_source",
        ),
        EcomaxNumberDescription(
            name="min_main_heat_source_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="max_main_heat_source_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="main_heat_source_hysteresis",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="critical_main_heat_source_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="main_heat_source_pump_extension_time",
        ),
        EcomaxNumberDescription(
            name="additional_heat_source",
        ),
        EcomaxNumberDescription(
            name="main_heat_source_off_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="additional_heat_source_pump_startup_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="hydraulic_diagram",
        ),
        EcomaxSwitchDescription(
            name="antifreeze",
        ),
        EcomaxNumberDescription(
            name="antifreeze_delay",
        ),
        EcomaxNumberDescription(
            name="circuit_lock_time",
        ),
        EcomaxNumberDescription(
            name="circuit_work_time",
        ),
        EcomaxNumberDescription(
            name="alert_out_c",
        ),
        EcomaxNumberDescription(
            name="alert_on_out_c",
        ),
        EcomaxNumberDescription(
            name="thermostat_hysteresis",
            multiplier=0.1,
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="critial_additional_heat_source_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="automatic_pump_lock_time",
        ),
        EcomaxNumberDescription(
            name="summer_mode",
        ),
        EcomaxNumberDescription(
            name="summer_mode_enable_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxNumberDescription(
            name="summer_mode_disable_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
    ),
}

ECOMAX_CONTROL_PARAMETER = EcomaxSwitchDescription(name=ATTR_ECOMAX_CONTROL)
THERMOSTAT_PROFILE_PARAMETER = EcomaxNumberDescription(name=ATTR_THERMOSTAT_PROFILE)


class EcomaxParametersStructure(StructureDecoder):
    """Represents an ecoMAX parameters structure."""

    __slots__ = ("_offset",)

    _offset: int

    def _ecomax_parameter(
        self, message: bytearray, start: int, end: int
    ) -> Generator[tuple[int, ParameterValues], None, None]:
        """Unpack an ecoMAX parameter."""
        for index in range(start, start + end):
            if parameter := unpack_parameter(message, self._offset):
                yield (index, parameter)

            self._offset += ECOMAX_PARAMETER_SIZE

    def decode(
        self, message: bytearray, offset: int = 0, data: dict[str, Any] | None = None
    ) -> tuple[dict[str, Any], int]:
        """Decode bytes and return message data and offset."""
        start = message[offset + 1]
        end = message[offset + 2]
        self._offset = offset + 3
        return (
            ensure_dict(
                data,
                {
                    ATTR_ECOMAX_PARAMETERS: list(
                        self._ecomax_parameter(message, start, end)
                    )
                },
            ),
            self._offset,
        )
