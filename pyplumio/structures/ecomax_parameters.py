"""Contains regulator parameter structure decoder."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Generator

from pyplumio.const import (
    ATTR_INDEX,
    ATTR_OFFSET,
    ATTR_SIZE,
    ATTR_VALUE,
    PERCENTAGE,
    ProductType,
    UnitOfMeasurement,
)
from pyplumio.devices import AddressableDevice
from pyplumio.frames import Request
from pyplumio.helpers.factory import factory
from pyplumio.helpers.parameter import (
    BinaryParameter,
    BinaryParameterDescription,
    Parameter,
    ParameterDescription,
    ParameterValues,
    unpack_parameter,
)
from pyplumio.helpers.typing import EventDataType, ParameterValueType
from pyplumio.structures import StructureDecoder
from pyplumio.structures.thermostat_parameters import ATTR_THERMOSTAT_PROFILE
from pyplumio.utils import ensure_dict

ATTR_ECOMAX_CONTROL: Final = "ecomax_control"
ATTR_ECOMAX_PARAMETERS: Final = "ecomax_parameters"

ECOMAX_PARAMETER_SIZE: Final = 3


class EcomaxParameter(Parameter):
    """Represents an ecoMAX parameter."""

    __slots__ = ()

    device: AddressableDevice
    description: EcomaxParameterDescription

    async def set(self, value: ParameterValueType, retries: int = 5) -> bool:
        """Set a parameter value."""
        if isinstance(value, (int, float)):
            value = int((value + self.description.offset) / self.description.multiplier)

        return await super().set(value, retries)

    @property
    def value(self) -> ParameterValueType:
        """A parameter value."""
        return (
            self.values.value - self.description.offset
        ) * self.description.multiplier

    @property
    def min_value(self) -> ParameterValueType:
        """Minimum allowed value."""
        return (
            self.values.min_value - self.description.offset
        ) * self.description.multiplier

    @property
    def max_value(self) -> ParameterValueType:
        """Maximum allowed value."""
        return (
            self.values.max_value - self.description.offset
        ) * self.description.multiplier

    @property
    def request(self) -> Request:
        """A request to change the parameter."""

        if self.description.name == ATTR_ECOMAX_CONTROL:
            return factory(
                "frames.requests.EcomaxControlRequest",
                recipient=self.device.address,
                data={
                    ATTR_VALUE: self.values.value,
                },
            )

        if self.description.name == ATTR_THERMOSTAT_PROFILE:
            return factory(
                "frames.requests.SetThermostatParameterRequest",
                recipient=self.device.address,
                data={
                    ATTR_INDEX: self._index,
                    ATTR_VALUE: self.values.value,
                    ATTR_OFFSET: 0,
                    ATTR_SIZE: 1,
                },
            )

        return factory(
            "frames.requests.SetEcomaxParameterRequest",
            recipient=self.device.address,
            data={
                ATTR_INDEX: self._index,
                ATTR_VALUE: self.values.value,
            },
        )


class EcomaxBinaryParameter(BinaryParameter, EcomaxParameter):
    """Represents an ecoMAX binary parameter."""


@dataclass
class EcomaxParameterDescription(ParameterDescription):
    """Represents an ecoMAX parameter description."""

    multiplier: float = 1
    offset: int = 0


@dataclass
class EcomaxBinaryParameterDescription(
    EcomaxParameterDescription, BinaryParameterDescription
):
    """Represents an ecoMAX binary parameter description."""


ECOMAX_PARAMETERS: dict[ProductType, tuple[EcomaxParameterDescription, ...]] = {
    ProductType.ECOMAX_P: (
        EcomaxParameterDescription(
            name="airflow_power_100", unit_of_measurement=PERCENTAGE
        ),
        EcomaxParameterDescription(
            name="airflow_power_50", unit_of_measurement=PERCENTAGE
        ),
        EcomaxParameterDescription(
            name="airflow_power_30", unit_of_measurement=PERCENTAGE
        ),
        EcomaxParameterDescription(
            name="boiler_power_100", unit_of_measurement=UnitOfMeasurement.KILO_WATT
        ),
        EcomaxParameterDescription(
            name="boiler_power_50", unit_of_measurement=UnitOfMeasurement.KILO_WATT
        ),
        EcomaxParameterDescription(
            name="boiler_power_30", unit_of_measurement=UnitOfMeasurement.KILO_WATT
        ),
        EcomaxParameterDescription(
            name="max_fan_boiler_power", unit_of_measurement=PERCENTAGE
        ),
        EcomaxParameterDescription(
            name="min_fan_boiler_power", unit_of_measurement=PERCENTAGE
        ),
        EcomaxParameterDescription(
            name="fuel_feeding_work_100", unit_of_measurement=UnitOfMeasurement.SECONDS
        ),
        EcomaxParameterDescription(
            name="fuel_feeding_work_50", unit_of_measurement=UnitOfMeasurement.SECONDS
        ),
        EcomaxParameterDescription(
            name="fuel_feeding_work_30", unit_of_measurement=UnitOfMeasurement.SECONDS
        ),
        EcomaxParameterDescription(
            name="fuel_feeding_pause_100", unit_of_measurement=UnitOfMeasurement.SECONDS
        ),
        EcomaxParameterDescription(
            name="fuel_feeding_pause_50", unit_of_measurement=UnitOfMeasurement.SECONDS
        ),
        EcomaxParameterDescription(
            name="fuel_feeding_pause_30", unit_of_measurement=UnitOfMeasurement.SECONDS
        ),
        EcomaxParameterDescription(
            name="cycle_duration", unit_of_measurement=UnitOfMeasurement.SECONDS
        ),
        EcomaxParameterDescription(
            name="h2_hysteresis", unit_of_measurement=UnitOfMeasurement.CELSIUS
        ),
        EcomaxParameterDescription(
            name="h1_hysteresis", unit_of_measurement=UnitOfMeasurement.CELSIUS
        ),
        EcomaxParameterDescription(
            name="heating_hysteresis", unit_of_measurement=UnitOfMeasurement.CELSIUS
        ),
        EcomaxBinaryParameterDescription(name="fuzzy_logic"),
        EcomaxParameterDescription(
            name="min_fuzzy_logic_power", unit_of_measurement=PERCENTAGE
        ),
        EcomaxParameterDescription(
            name="max_fuzzy_logic_power", unit_of_measurement=PERCENTAGE
        ),
        EcomaxParameterDescription(
            name="min_boiler_power", unit_of_measurement=UnitOfMeasurement.KILO_WATT
        ),
        EcomaxParameterDescription(
            name="max_boiler_power", unit_of_measurement=UnitOfMeasurement.KILO_WATT
        ),
        EcomaxParameterDescription(
            name="min_fan_power", unit_of_measurement=PERCENTAGE
        ),
        EcomaxParameterDescription(
            name="max_fan_power", unit_of_measurement=PERCENTAGE
        ),
        EcomaxParameterDescription(
            name="reduction_airflow_temp", unit_of_measurement=UnitOfMeasurement.CELSIUS
        ),
        EcomaxParameterDescription(
            name="fan_power_gain", unit_of_measurement=PERCENTAGE
        ),
        EcomaxParameterDescription(
            name="fuzzy_logic_fuel_flow_correction",
            unit_of_measurement=PERCENTAGE,
        ),
        EcomaxParameterDescription(
            name="fuel_flow_correction", unit_of_measurement=PERCENTAGE
        ),
        EcomaxParameterDescription(
            name="airflow_correction_100", unit_of_measurement=PERCENTAGE
        ),
        EcomaxParameterDescription(
            name="feeder_correction_100", unit_of_measurement=PERCENTAGE
        ),
        EcomaxParameterDescription(
            name="airflow_correction_50", unit_of_measurement=PERCENTAGE
        ),
        EcomaxParameterDescription(
            name="feeder_correction_50", unit_of_measurement=PERCENTAGE
        ),
        EcomaxParameterDescription(
            name="airflow_correction_30", unit_of_measurement=PERCENTAGE
        ),
        EcomaxParameterDescription(
            name="feeder_correction_30", unit_of_measurement=PERCENTAGE
        ),
        EcomaxParameterDescription(
            name="grate_airflow_power", unit_of_measurement=PERCENTAGE
        ),
        EcomaxParameterDescription(
            name="grate_heating_hysteresis",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxParameterDescription(
            name="supervision_airflow_work",
            unit_of_measurement=UnitOfMeasurement.SECONDS,
        ),
        EcomaxParameterDescription(
            name="supervision_airflow_pause",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        EcomaxParameterDescription(
            name="grate_heating_temp", unit_of_measurement=UnitOfMeasurement.CELSIUS
        ),
        EcomaxParameterDescription(
            name="grate_fuel_detection_time",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        EcomaxParameterDescription(
            name="kindling_airflow_power", unit_of_measurement=PERCENTAGE
        ),
        EcomaxParameterDescription(
            name="kindling_low_airflow_power",
            unit_of_measurement=PERCENTAGE,
        ),
        EcomaxParameterDescription(
            name="kindling_airflow_delay", unit_of_measurement=UnitOfMeasurement.SECONDS
        ),
        EcomaxParameterDescription(
            name="kindling_test_time", unit_of_measurement=UnitOfMeasurement.SECONDS
        ),
        EcomaxParameterDescription(name="kindling_feeder_work"),
        EcomaxParameterDescription(
            name="kindling_feeder_dose", unit_of_measurement=UnitOfMeasurement.GRAMS
        ),
        EcomaxParameterDescription(
            name="kindling_time", unit_of_measurement=UnitOfMeasurement.MINUTES
        ),
        EcomaxParameterDescription(
            name="warming_up_time", unit_of_measurement=UnitOfMeasurement.MINUTES
        ),
        EcomaxParameterDescription(
            name="kindling_finish_exhaust_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxParameterDescription(
            name="kindling_finish_threshold_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxParameterDescription(
            name="kindling_fumes_delta_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxParameterDescription(
            name="kindling_delta_temp", unit_of_measurement=UnitOfMeasurement.CELSIUS
        ),
        EcomaxParameterDescription(
            name="kindling_min_power_time",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        EcomaxParameterDescription(
            name="stabilization_time",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        EcomaxParameterDescription(
            name="stabilization_airflow_power",
            unit_of_measurement=PERCENTAGE,
        ),
        EcomaxParameterDescription(name="supervision_time"),
        EcomaxParameterDescription(
            name="supervision_feeder_work",
            unit_of_measurement=UnitOfMeasurement.SECONDS,
        ),
        EcomaxParameterDescription(
            name="supervision_feeder_dose",
            unit_of_measurement=UnitOfMeasurement.GRAMS,
        ),
        EcomaxParameterDescription(
            name="supervision_feeder_pause",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        EcomaxParameterDescription(
            name="supervision_cycle_duration",
            unit_of_measurement=UnitOfMeasurement.SECONDS,
        ),
        EcomaxParameterDescription(
            name="supervision_airflow_power",
            unit_of_measurement=PERCENTAGE,
        ),
        EcomaxParameterDescription(
            name="supervision_fan_pause", unit_of_measurement=UnitOfMeasurement.MINUTES
        ),
        EcomaxParameterDescription(
            name="supervision_fan_work", unit_of_measurement=UnitOfMeasurement.SECONDS
        ),
        EcomaxParameterDescription(name="increase_fan_support_mode"),
        EcomaxParameterDescription(
            name="burning_off_max_time", unit_of_measurement=UnitOfMeasurement.MINUTES
        ),
        EcomaxParameterDescription(
            name="burning_off_min_time", unit_of_measurement=UnitOfMeasurement.MINUTES
        ),
        EcomaxParameterDescription(name="burning_off_time"),
        EcomaxParameterDescription(
            name="burning_off_airflow_power",
            unit_of_measurement=PERCENTAGE,
        ),
        EcomaxParameterDescription(name="burning_off_airflow_work"),
        EcomaxParameterDescription(name="burning_off_airflow_pause"),
        EcomaxParameterDescription(
            name="start_burning_off", unit_of_measurement=PERCENTAGE
        ),
        EcomaxParameterDescription(
            name="stop_burning_off", unit_of_measurement=PERCENTAGE
        ),
        EcomaxParameterDescription(name="cleaning_begin_time"),
        EcomaxParameterDescription(name="burning_off_cleaning_time"),
        EcomaxParameterDescription(
            name="cleaning_airflow_power", unit_of_measurement=PERCENTAGE
        ),
        EcomaxParameterDescription(name="warming_up_pause_time"),
        EcomaxParameterDescription(name="warming_up_cycle_time"),
        EcomaxParameterDescription(name="remind_time"),
        EcomaxBinaryParameterDescription(name="lambda_control"),
        EcomaxParameterDescription(name="lambda_correction_range"),
        EcomaxParameterDescription(name="oxygen_100"),
        EcomaxParameterDescription(name="oxygen_50"),
        EcomaxParameterDescription(name="oxygen_30"),
        EcomaxParameterDescription(name="fuzzy_logic_oxygen_correction"),
        EcomaxParameterDescription(
            name="max_fuel_flow",
            multiplier=0.1,
            unit_of_measurement=UnitOfMeasurement.KILOGRAMS_PER_HOUR,
        ),
        EcomaxParameterDescription(name="feeder_calibration"),
        EcomaxParameterDescription(name="fuel_factor"),
        EcomaxParameterDescription(
            name="fuel_calorific_value",
            multiplier=0.1,
            unit_of_measurement=UnitOfMeasurement.KILO_WATT_HOUR_PER_KILOGRAM,
        ),
        EcomaxParameterDescription(
            name="fuel_detection_time", unit_of_measurement=UnitOfMeasurement.MINUTES
        ),
        EcomaxParameterDescription(
            name="fuel_detection_exhaust_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxBinaryParameterDescription(name="schedule_feeder_2"),
        EcomaxParameterDescription(name="feed2_h1"),
        EcomaxParameterDescription(name="feed2_h2"),
        EcomaxParameterDescription(name="feed2_h3"),
        EcomaxParameterDescription(name="feed2_h4"),
        EcomaxParameterDescription(name="feed2_work"),
        EcomaxParameterDescription(name="feed2_pause"),
        EcomaxParameterDescription(
            name="heating_target_temp", unit_of_measurement=UnitOfMeasurement.CELSIUS
        ),
        EcomaxParameterDescription(
            name="min_heating_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxParameterDescription(
            name="max_heating_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxParameterDescription(
            name="heating_pump_enable_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxParameterDescription(
            name="pause_heating_for_water_heater",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        EcomaxParameterDescription(name="thermostat_pause"),
        EcomaxParameterDescription(name="thermostat_work"),
        EcomaxParameterDescription(
            name="increase_heating_temp_for_water_heater",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxBinaryParameterDescription(name="weather_control"),
        EcomaxParameterDescription(name="heating_curve", multiplier=0.1),
        EcomaxParameterDescription(
            name="heating_curve_shift",
            offset=20,
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxParameterDescription(name="weather_factor"),
        EcomaxParameterDescription(name="thermostat_operation"),
        EcomaxBinaryParameterDescription(name="thermostat_mode"),
        EcomaxParameterDescription(
            name="thermostat_decrease_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxBinaryParameterDescription(name="disable_pump_on_thermostat"),
        EcomaxParameterDescription(
            name="boiler_alert_temp", unit_of_measurement=UnitOfMeasurement.CELSIUS
        ),
        EcomaxParameterDescription(
            name="max_feeder_temp", unit_of_measurement=UnitOfMeasurement.CELSIUS
        ),
        EcomaxParameterDescription(
            name="external_boiler_temp", unit_of_measurement=UnitOfMeasurement.CELSIUS
        ),
        EcomaxParameterDescription(
            name="alert_notify", unit_of_measurement=UnitOfMeasurement.CELSIUS
        ),
        EcomaxParameterDescription(
            name="pump_hysteresis", unit_of_measurement=UnitOfMeasurement.CELSIUS
        ),
        EcomaxParameterDescription(
            name="water_heater_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxParameterDescription(
            name="min_water_heater_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxParameterDescription(
            name="max_water_heater_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxParameterDescription(name="water_heater_work_mode"),
        EcomaxParameterDescription(
            name="water_heater_hysteresis",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxBinaryParameterDescription(name="water_heater_disinfection"),
        EcomaxParameterDescription(name="summer_mode"),
        EcomaxParameterDescription(
            name="summer_mode_enable_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxParameterDescription(
            name="summer_mode_disable_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxParameterDescription(
            name="water_heater_work_extension",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        EcomaxBinaryParameterDescription(name="circulation_pump"),
        EcomaxParameterDescription(
            name="circulation_pause", unit_of_measurement=UnitOfMeasurement.MINUTES
        ),
        EcomaxParameterDescription(
            name="circulation_work", unit_of_measurement=UnitOfMeasurement.MINUTES
        ),
        EcomaxParameterDescription(
            name="circulation_start_temp", unit_of_measurement=UnitOfMeasurement.CELSIUS
        ),
        EcomaxBinaryParameterDescription(name="buffer_control"),
        EcomaxParameterDescription(
            name="max_buffer_temp", unit_of_measurement=UnitOfMeasurement.CELSIUS
        ),
        EcomaxParameterDescription(
            name="min_buffer_temp", unit_of_measurement=UnitOfMeasurement.CELSIUS
        ),
        EcomaxParameterDescription(
            name="buffer_hysteresis", unit_of_measurement=UnitOfMeasurement.CELSIUS
        ),
        EcomaxParameterDescription(
            name="buffer_load_start", unit_of_measurement=UnitOfMeasurement.CELSIUS
        ),
        EcomaxParameterDescription(
            name="buffer_load_stop", unit_of_measurement=UnitOfMeasurement.CELSIUS
        ),
    ),
    ProductType.ECOMAX_I: (
        EcomaxParameterDescription(
            name="water_heater_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxBinaryParameterDescription(name="water_heater_priority"),
        EcomaxParameterDescription(name="water_heater_support"),
        EcomaxParameterDescription(
            name="min_water_heater_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxParameterDescription(
            name="max_water_heater_target_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxParameterDescription(
            name="water_heater_work_extension",
            unit_of_measurement=UnitOfMeasurement.MINUTES,
        ),
        EcomaxParameterDescription(
            name="water_heater_hysteresis",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxBinaryParameterDescription(name="water_heater_disinfection"),
        EcomaxParameterDescription(name="water_heater_work_mode"),
        EcomaxBinaryParameterDescription(name="solar_support"),
        EcomaxParameterDescription(
            name="solar_pump_on_delta_temp",
            multiplier=0.1,
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxParameterDescription(
            name="solar_pump_off_delta_temp",
            multiplier=0.1,
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxParameterDescription(
            name="min_collector_temp", unit_of_measurement=UnitOfMeasurement.CELSIUS
        ),
        EcomaxParameterDescription(
            name="max_collector_temp", unit_of_measurement=UnitOfMeasurement.CELSIUS
        ),
        EcomaxParameterDescription(
            name="collector_off_temp", unit_of_measurement=UnitOfMeasurement.CELSIUS
        ),
        EcomaxParameterDescription(name="min_pump_revolutions"),
        EcomaxParameterDescription(
            name="solar_antifreeze", unit_of_measurement=UnitOfMeasurement.CELSIUS
        ),
        EcomaxBinaryParameterDescription(name="circulation_pump"),
        EcomaxParameterDescription(
            name="circulation_pause", unit_of_measurement=UnitOfMeasurement.MINUTES
        ),
        EcomaxParameterDescription(
            name="circulation_work", unit_of_measurement=UnitOfMeasurement.MINUTES
        ),
        EcomaxParameterDescription(
            name="circulation_start_temp", unit_of_measurement=UnitOfMeasurement.CELSIUS
        ),
        EcomaxParameterDescription(name="main_heat_source"),
        EcomaxParameterDescription(
            name="min_main_heat_source_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxParameterDescription(
            name="max_main_heat_source_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxParameterDescription(
            name="main_heat_source_hysteresis",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxParameterDescription(
            name="critical_main_heat_source_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxParameterDescription(name="main_heat_source_pump_extension_time"),
        EcomaxParameterDescription(name="additional_heat_source"),
        EcomaxBinaryParameterDescription(
            name="main_heat_source_off_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxParameterDescription(
            name="additional_heat_source_pump_startup_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxParameterDescription(name="hydraulic_diagram"),
        EcomaxBinaryParameterDescription(name="antifreeze"),
        EcomaxParameterDescription(name="antifreeze_delay"),
        EcomaxParameterDescription(name="circuit_lock_time"),
        EcomaxParameterDescription(name="circuit_work_time"),
        EcomaxParameterDescription(name="alert_out_c"),
        EcomaxParameterDescription(name="alert_on_out_c"),
        EcomaxParameterDescription(
            name="thermostat_hysteresis",
            multiplier=0.1,
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxParameterDescription(
            name="critial_additional_heat_source_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxParameterDescription(name="automatic_pump_lock_time"),
        EcomaxParameterDescription(name="summer_mode"),
        EcomaxParameterDescription(
            name="summer_mode_enable_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
        EcomaxParameterDescription(
            name="summer_mode_disable_temp",
            unit_of_measurement=UnitOfMeasurement.CELSIUS,
        ),
    ),
}

ECOMAX_CONTROL_PARAMETER = EcomaxBinaryParameterDescription(name=ATTR_ECOMAX_CONTROL)
THERMOSTAT_PROFILE_PARAMETER = EcomaxParameterDescription(name=ATTR_THERMOSTAT_PROFILE)


class EcomaxParametersStructure(StructureDecoder):
    """Represents an ecoMAX parameters structure."""

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
        self, message: bytearray, offset: int = 0, data: EventDataType | None = None
    ) -> tuple[EventDataType, int]:
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
