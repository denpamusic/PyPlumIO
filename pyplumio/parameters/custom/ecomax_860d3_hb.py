"""Contains custom parameters for ecoMAX 860D3-HB."""

from __future__ import annotations

from pyplumio.parameters.custom import custom_parameters, number, switch

PARAMETERS = custom_parameters(
    model="ecoMAX 860D3-HB",
    id=48,
    patches={
        # Summer mode
        "summer_mode_disable_temp": number("__unknown_parameter_1"),
        "water_heater_target_temp": number("summer_mode"),
        "min_water_heater_target_temp": number("summer_mode_enable_temp", unit="°C"),
        "max_water_heater_target_temp": number("summer_mode_disable_temp", unit="°C"),
        # Water heater
        "disable_pump_on_thermostat": number("water_heater_target_temp", unit="°C"),
        "boiler_alert_temp": number("min_water_heater_target_temp", unit="°C"),
        "max_feeder_temp": number("max_water_heater_target_temp", unit="°C"),
        "water_heater_work_mode": number("water_heater_feeding_extension"),
        "external_boiler_temp": number("water_heater_work_mode"),
        "alert_notify": number("water_heater_hysteresis", unit="°C"),
        "pump_hysteresis": switch("water_heater_disinfection"),
    },
)
