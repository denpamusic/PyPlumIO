"""Contains regulator parameter structure decoder."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final, List, Optional, Tuple, Type

from pyplumio import util
from pyplumio.const import ATTR_INDEX, ATTR_OFFSET, ATTR_VALUE
from pyplumio.devices import Addressable
from pyplumio.frames import Request
from pyplumio.helpers.factory import factory
from pyplumio.helpers.parameter import BinaryParameter, Parameter, ParameterDescription
from pyplumio.helpers.typing import (
    DeviceDataType,
    ParameterDataType,
    ParameterValueType,
)
from pyplumio.structures import StructureDecoder, ensure_device_data
from pyplumio.structures.thermostat_parameters import ATTR_THERMOSTAT_PROFILE

ATTR_ECOMAX_CONTROL: Final = "ecomax_control"
ATTR_ECOMAX_PARAMETERS: Final = "ecomax_parameters"


class EcomaxParameter(Parameter):
    """Represents ecoMAX parameter."""

    device: Addressable
    description: EcomaxParameterDescription

    async def set(self, value: ParameterValueType, retries: int = 5) -> bool:
        """Set parameter value."""
        if isinstance(value, (int, float)):
            value *= self.description.multiplier

        return await super().set(value, retries)

    @property
    def value(self) -> ParameterValueType:
        """Return parameter value."""
        return self._value / self.description.multiplier

    @property
    def min_value(self) -> ParameterValueType:
        """Return minimum allowed value."""
        return self._min_value / self.description.multiplier

    @property
    def max_value(self) -> ParameterValueType:
        """Return maximum allowed value."""
        return self._max_value / self.description.multiplier

    @property
    def request(self) -> Request:
        """Return request to change the parameter."""

        if self.description.name == ATTR_ECOMAX_CONTROL:
            return factory(
                "frames.requests.EcomaxControlRequest",
                recipient=self.device.address,
                data={
                    ATTR_VALUE: self._value,
                },
            )

        if self.description.name == ATTR_THERMOSTAT_PROFILE:
            return factory(
                "frames.requests.SetThermostatParameterRequest",
                recipient=self.device.address,
                data={
                    ATTR_INDEX: self._index,
                    ATTR_VALUE: self._value,
                    ATTR_OFFSET: 0,
                },
            )

        return factory(
            "frames.requests.SetEcomaxParameterRequest",
            recipient=self.device.address,
            data={
                ATTR_INDEX: self._index,
                ATTR_VALUE: self._value,
            },
        )


class EcomaxBinaryParameter(BinaryParameter, EcomaxParameter):
    """Represents ecoMAX binary parameter."""


@dataclass
class EcomaxParameterDescription(ParameterDescription):
    """Represent thermostat parameter description."""

    cls: Type[EcomaxParameter] = EcomaxParameter
    multiplier: int = 1


ECOMAX_P_PARAMETERS: Tuple[EcomaxParameterDescription, ...] = (
    EcomaxParameterDescription(name="airflow_power_100"),
    EcomaxParameterDescription(name="airflow_power_50"),
    EcomaxParameterDescription(name="airflow_power_30"),
    EcomaxParameterDescription(name="power_100"),
    EcomaxParameterDescription(name="power_50"),
    EcomaxParameterDescription(name="power_30"),
    EcomaxParameterDescription(name="max_fan_boiler_power"),
    EcomaxParameterDescription(name="min_fan_boiler_power"),
    EcomaxParameterDescription(name="fuel_feeding_time_100"),
    EcomaxParameterDescription(name="fuel_feeding_time_50"),
    EcomaxParameterDescription(name="fuel_feeding_time_30"),
    EcomaxParameterDescription(name="fuel_feeding_break_100"),
    EcomaxParameterDescription(name="fuel_feeding_break_50"),
    EcomaxParameterDescription(name="fuel_feeding_break_30"),
    EcomaxParameterDescription(name="cycle_time"),
    EcomaxParameterDescription(name="h2_hysteresis"),
    EcomaxParameterDescription(name="h1_hysteresis"),
    EcomaxParameterDescription(name="heating_hysteresis"),
    EcomaxParameterDescription(name="fuzzy_logic", cls=EcomaxBinaryParameter),
    EcomaxParameterDescription(name="min_fuzzy_logic_power"),
    EcomaxParameterDescription(name="max_fuzzy_logic_power"),
    EcomaxParameterDescription(name="min_boiler_power"),
    EcomaxParameterDescription(name="max_boiler_power"),
    EcomaxParameterDescription(name="min_fan_power"),
    EcomaxParameterDescription(name="max_fan_power"),
    EcomaxParameterDescription(name="reduction_airflow_temp"),
    EcomaxParameterDescription(name="fan_power_gain"),
    EcomaxParameterDescription(name="fuel_flow_correction_fuzzy_logic"),
    EcomaxParameterDescription(name="fuel_flow_correction"),
    EcomaxParameterDescription(name="airflow_correction_100"),
    EcomaxParameterDescription(name="feeder_correction_100"),
    EcomaxParameterDescription(name="airflow_correction_50"),
    EcomaxParameterDescription(name="feeder_correction_50"),
    EcomaxParameterDescription(name="airflow_correction_30"),
    EcomaxParameterDescription(name="feeder_correction_30"),
    EcomaxParameterDescription(name="airflow_power_grate"),
    EcomaxParameterDescription(name="boiler_hysteresis_grate"),
    EcomaxParameterDescription(name="supervision_work_airflow"),
    EcomaxParameterDescription(name="supervision_work_airflow_brake"),
    EcomaxParameterDescription(name="heating_temp_grate"),
    EcomaxParameterDescription(name="fuel_detection_time_grate"),
    EcomaxParameterDescription(name="airflow_power_kindle"),
    EcomaxParameterDescription(name="small_airflow_power_kindle"),
    EcomaxParameterDescription(name="airflow_kindle_delay"),
    EcomaxParameterDescription(name="scavenge_kindle"),
    EcomaxParameterDescription(name="feeder_kindle"),
    EcomaxParameterDescription(name="feeder_kindle_weight"),
    EcomaxParameterDescription(name="kindle_time"),
    EcomaxParameterDescription(name="warming_up_time"),
    EcomaxParameterDescription(name="kindle_finish_fumes_temp"),
    EcomaxParameterDescription(name="kindle_finish_threshold"),
    EcomaxParameterDescription(name="kindle_fumes_delta_temp"),
    EcomaxParameterDescription(name="kindle_delta_t"),
    EcomaxParameterDescription(name="min_kindle_power_time"),
    EcomaxParameterDescription(name="scavenge_after_kindle"),
    EcomaxParameterDescription(name="airflow_power_after_kindle"),
    EcomaxParameterDescription(name="supervision_time"),
    EcomaxParameterDescription(name="feed_time_supervision"),
    EcomaxParameterDescription(name="feed_time_supervision_weight"),
    EcomaxParameterDescription(name="feed_supervision_break"),
    EcomaxParameterDescription(name="supervision_cycle_duration"),
    EcomaxParameterDescription(name="airflow_power_supervision"),
    EcomaxParameterDescription(name="fan_supervison_break"),
    EcomaxParameterDescription(name="fan_work_supervision"),
    EcomaxParameterDescription(name="increase_fan_support_mode"),
    EcomaxParameterDescription(name="max_extinguish_time"),
    EcomaxParameterDescription(name="min_extinguish_time"),
    EcomaxParameterDescription(name="extinguish_time"),
    EcomaxParameterDescription(name="airflow_power_extinguish"),
    EcomaxParameterDescription(name="airflow_work_extinguish"),
    EcomaxParameterDescription(name="airflow_brake_extinguish"),
    EcomaxParameterDescription(name="scavenge_start_extinguish"),
    EcomaxParameterDescription(name="scavenge_stop_extinguish"),
    EcomaxParameterDescription(name="clean_begin_time"),
    EcomaxParameterDescription(name="extinguish_clean_time"),
    EcomaxParameterDescription(name="airflow_power_clean"),
    EcomaxParameterDescription(name="warming_up_brake_time"),
    EcomaxParameterDescription(name="warming_up_cycle_time"),
    EcomaxParameterDescription(name="remind_time"),
    EcomaxParameterDescription(name="lambda_work", cls=EcomaxBinaryParameter),
    EcomaxParameterDescription(name="lambda_correction_range"),
    EcomaxParameterDescription(name="oxygen_100"),
    EcomaxParameterDescription(name="oxygen_50"),
    EcomaxParameterDescription(name="oxygen_30"),
    EcomaxParameterDescription(name="oxygen_correction_fl"),
    EcomaxParameterDescription(name="fuel_flow_kg_h", multiplier=10),
    EcomaxParameterDescription(name="feeder_calibration"),
    EcomaxParameterDescription(name="fuel_factor"),
    EcomaxParameterDescription(name="fuel_calorific_value_kwh_kg", multiplier=10),
    EcomaxParameterDescription(name="fuel_detection_time"),
    EcomaxParameterDescription(name="fuel_detection_fumes_temp"),
    EcomaxParameterDescription(name="schedule_feeder_2"),
    EcomaxParameterDescription(name="feed2_h1"),
    EcomaxParameterDescription(name="feed2_h2"),
    EcomaxParameterDescription(name="feed2_h3"),
    EcomaxParameterDescription(name="feed2_h4"),
    EcomaxParameterDescription(name="feed2_work"),
    EcomaxParameterDescription(name="feed2_break"),
    EcomaxParameterDescription(name="heating_target_temp"),
    EcomaxParameterDescription(name="min_heating_target_temp"),
    EcomaxParameterDescription(name="max_heating_target_temp"),
    EcomaxParameterDescription(name="heating_pump_on_temp"),
    EcomaxParameterDescription(name="pause_heating_for_water_heater"),
    EcomaxParameterDescription(name="pause_term"),
    EcomaxParameterDescription(name="work_term"),
    EcomaxParameterDescription(name="increase_heating_temp_for_water_heater"),
    EcomaxParameterDescription(
        name="heating_weather_control", cls=EcomaxBinaryParameter
    ),
    EcomaxParameterDescription(name="heating_heat_curve", multiplier=10),
    EcomaxParameterDescription(name="heating_heat_curve_shift", multiplier=10),
    EcomaxParameterDescription(name="weather_factor"),
    EcomaxParameterDescription(name="term_boiler_operation"),
    EcomaxParameterDescription(name="term_boiler_mode", cls=EcomaxBinaryParameter),
    EcomaxParameterDescription(name="decrease_set_heating_term"),
    EcomaxParameterDescription(name="term_pump_off"),
    EcomaxParameterDescription(name="boiler_alert_temp"),
    EcomaxParameterDescription(name="max_feeder_temp"),
    EcomaxParameterDescription(name="external_boiler_temp"),
    EcomaxParameterDescription(name="alarm_notify"),
    EcomaxParameterDescription(name="pump_hysteresis"),
    EcomaxParameterDescription(name="water_heater_target_temp"),
    EcomaxParameterDescription(name="min_water_heater_target_temp"),
    EcomaxParameterDescription(name="max_water_heater_target_temp"),
    EcomaxParameterDescription(name="water_heater_work_mode"),
    EcomaxParameterDescription(name="water_heater_hysteresis"),
    EcomaxParameterDescription(
        name="water_heater_disinfection", cls=EcomaxBinaryParameter
    ),
    EcomaxParameterDescription(name="summer_mode"),
    EcomaxParameterDescription(name="summer_mode_on_temp"),
    EcomaxParameterDescription(name="summer_mode_off_temp"),
    EcomaxParameterDescription(name="water_heater_feeding_extension"),
    EcomaxParameterDescription(name="circulation_control", cls=EcomaxBinaryParameter),
    EcomaxParameterDescription(name="circulation_pause_time"),
    EcomaxParameterDescription(name="circulation_work_time"),
    EcomaxParameterDescription(name="circulation_start_temp"),
    EcomaxParameterDescription(name="buffer_control"),
    EcomaxParameterDescription(name="max_buffer_temp"),
    EcomaxParameterDescription(name="min_buffer_temp"),
    EcomaxParameterDescription(name="buffer_hysteresis"),
    EcomaxParameterDescription(name="buffer_load_start"),
    EcomaxParameterDescription(name="buffer_load_stop"),
)

ECOMAX_I_PARAMETERS: Tuple[EcomaxParameterDescription, ...] = (
    EcomaxParameterDescription(name="water_heater_target_temp"),
    EcomaxParameterDescription(name="water_heater_priority", cls=EcomaxBinaryParameter),
    EcomaxParameterDescription(name="water_heater_support"),
    EcomaxParameterDescription(name="min_water_heater_target_temp"),
    EcomaxParameterDescription(name="max_water_heater_target_temp"),
    EcomaxParameterDescription(name="water_heater_feeding_extension_time"),
    EcomaxParameterDescription(name="water_heater_hysteresis"),
    EcomaxParameterDescription(
        name="water_heater_disinfection", cls=EcomaxBinaryParameter
    ),
    EcomaxParameterDescription(name="water_heater_work_mode"),
    EcomaxParameterDescription(name="solar_support", cls=EcomaxBinaryParameter),
    EcomaxParameterDescription(name="solar_pump_on_delta_temp", multiplier=10),
    EcomaxParameterDescription(name="solar_pump_off_delta_temp", multiplier=10),
    EcomaxParameterDescription(name="min_collector_temp"),
    EcomaxParameterDescription(name="max_collector_temp"),
    EcomaxParameterDescription(name="collector_off_temp"),
    EcomaxParameterDescription(name="min_pump_revolutions"),
    EcomaxParameterDescription(name="solar_antifreeze"),
    EcomaxParameterDescription(name="circulation_control", cls=EcomaxBinaryParameter),
    EcomaxParameterDescription(name="circulation_pause_time"),
    EcomaxParameterDescription(name="circulation_work_time"),
    EcomaxParameterDescription(name="circulation_start_temp"),
    EcomaxParameterDescription(name="main_heat_source"),
    EcomaxParameterDescription(name="min_main_heat_source_temp"),
    EcomaxParameterDescription(name="max_main_heat_source_temp"),
    EcomaxParameterDescription(name="main_heat_source_hysteresis"),
    EcomaxParameterDescription(name="critical_main_heat_source_temp"),
    EcomaxParameterDescription(name="main_heat_source_pump_extension_time"),
    EcomaxParameterDescription(name="additional_heat_source"),
    EcomaxParameterDescription(
        name="main_heat_source_off_temp", cls=EcomaxBinaryParameter
    ),
    EcomaxParameterDescription(name="additional_heat_source_pump_startup_temp"),
    EcomaxParameterDescription(name="hydraulic_diagram"),
    EcomaxParameterDescription(name="antifreeze"),
    EcomaxParameterDescription(name="antifreeze_delay"),
    EcomaxParameterDescription(name="circuit_lock_time"),
    EcomaxParameterDescription(name="circuit_work_time"),
    EcomaxParameterDescription(name="alarm_out_c"),
    EcomaxParameterDescription(name="alarm_on_out_c"),
    EcomaxParameterDescription(name="thermostat_hysteresis", multiplier=10),
    EcomaxParameterDescription(name="critial_additional_heat_source_temp"),
    EcomaxParameterDescription(name="automatic_pump_lock_time"),
    EcomaxParameterDescription(name="summer_mode"),
    EcomaxParameterDescription(name="summer_mode_on_temp"),
    EcomaxParameterDescription(name="summer_mode_off_temp"),
)

ECOMAX_CONTROL_PARAMETER = EcomaxParameterDescription(
    name=ATTR_ECOMAX_CONTROL, cls=EcomaxBinaryParameter
)

THERMOSTAT_PROFILE_PARAMETER = EcomaxParameterDescription(name=ATTR_THERMOSTAT_PROFILE)


class EcomaxParametersStructure(StructureDecoder):
    """Represents ecoMAX parameters data structure."""

    def decode(
        self, message: bytearray, offset: int = 0, data: Optional[DeviceDataType] = None
    ) -> Tuple[DeviceDataType, int]:
        """Decode bytes and return message data and offset."""
        first_index = message[offset + 1]
        last_index = message[offset + 2]
        offset += 3
        ecomax_parameters: List[Tuple[int, ParameterDataType]] = []
        for index in range(first_index, first_index + last_index):
            parameter = util.unpack_parameter(message, offset)
            if parameter is not None:
                ecomax_parameters.append((index, parameter))

            offset += 3

        return (
            ensure_device_data(data, {ATTR_ECOMAX_PARAMETERS: ecomax_parameters}),
            offset,
        )
