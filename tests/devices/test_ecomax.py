"""Contains tests for the ecoMAX device."""

import asyncio
from datetime import timedelta
import logging
from typing import Any, cast
from unittest.mock import AsyncMock, Mock, patch

import pytest

from pyplumio.const import (
    ATTR_FRAME_ERRORS,
    ATTR_INDEX,
    ATTR_OFFSET,
    ATTR_PARAMETER,
    ATTR_SCHEDULE,
    ATTR_SENSORS,
    ATTR_SETUP,
    ATTR_SIZE,
    ATTR_STATE,
    ATTR_SWITCH,
    ATTR_TYPE,
    ATTR_VALUE,
    STATE_OFF,
    STATE_ON,
    DeviceState,
    DeviceType,
    FrameType,
    State,
    UnitOfMeasurement,
)
from pyplumio.devices.ecomax import (
    ATTR_FUEL_BURNED,
    ATTR_MIXERS,
    ATTR_THERMOSTATS,
    REQUIRED,
    EcoMAX,
)
from pyplumio.devices.mixer import Mixer
from pyplumio.devices.thermostat import Thermostat
from pyplumio.exceptions import RequestError
from pyplumio.frames import Request, Response
from pyplumio.frames.messages import SensorDataMessage
from pyplumio.frames.requests import (
    AlertsRequest,
    EcomaxControlRequest,
    EcomaxParametersRequest,
    SetEcomaxParameterRequest,
    SetScheduleRequest,
    SetThermostatParameterRequest,
)
from pyplumio.frames.responses import (
    EcomaxParametersResponse,
    MixerParametersResponse,
    SchedulesResponse,
    ThermostatParametersResponse,
)
from pyplumio.parameters.ecomax import PARAMETER_TYPES, EcomaxNumber, EcomaxSwitch
from pyplumio.structures.ecomax_parameters import ATTR_ECOMAX_CONTROL
from pyplumio.structures.frame_versions import ATTR_FRAME_VERSIONS
from pyplumio.structures.fuel_consumption import ATTR_FUEL_CONSUMPTION
from pyplumio.structures.mixer_parameters import ATTR_MIXER_PARAMETERS
from pyplumio.structures.mixer_sensors import (
    ATTR_MIXER_SENSORS,
    ATTR_MIXERS_AVAILABLE,
    ATTR_MIXERS_CONNECTED,
)
from pyplumio.structures.network_info import ATTR_NETWORK, NetworkInfo
from pyplumio.structures.schedules import (
    ATTR_SCHEDULE_PARAMETER,
    ATTR_SCHEDULE_SWITCH,
    ATTR_SCHEDULES,
    Schedule,
    ScheduleDay,
    ScheduleNumber,
    ScheduleSwitch,
)
from pyplumio.structures.thermostat_parameters import (
    ATTR_THERMOSTAT_PARAMETERS,
    ATTR_THERMOSTAT_PROFILE,
)
from pyplumio.structures.thermostat_sensors import (
    ATTR_THERMOSTAT_SENSORS,
    ATTR_THERMOSTATS_AVAILABLE,
    ATTR_THERMOSTATS_CONNECTED,
)
from tests.conftest import (
    UNDEFINED,
    class_from_json,
    equal_parameter_value,
    json_test_data,
)


@patch("asyncio.Queue.put_nowait")
@patch("pyplumio.devices.PhysicalDevice.handle_frame")
@patch("pyplumio.frames.Request.response", return_value=Mock(spec=Response))
async def test_ecomax_handle_frame(
    mock_response, mock_handle_frame, mock_put_nowait, ecomax: EcoMAX
) -> None:
    """Test ecoMAX frame handling."""
    request = Request()
    ecomax.handle_frame(request)
    args = mock_response.call_args[1]
    assert isinstance(args["data"][ATTR_NETWORK], NetworkInfo)
    mock_put_nowait.assert_called_once_with(mock_response.return_value)
    mock_handle_frame.assert_called_once_with(request)


@pytest.mark.parametrize(
    ("frame_type", "frame_request"),
    [
        (FrameType.REQUEST_ALERTS, AlertsRequest(recipient=DeviceType.ECOMAX)),
        (
            FrameType.REQUEST_ECOMAX_PARAMETER_CHANGES,
            EcomaxParametersRequest(recipient=DeviceType.ECOMAX),
        ),
    ],
)
@patch("asyncio.Queue.put_nowait")
@class_from_json(SensorDataMessage, "messages/sensor_data.json", arguments=("message",))
async def test_frame_versions_tracker(
    mock_put_nowait,
    ecomax: EcoMAX,
    sensor_data: SensorDataMessage,
    frame_type: FrameType,
    frame_request: Request,
) -> None:
    """Test frame version tracker."""

    def _frame_version_data(frame: FrameType, version: int) -> dict[str, Any]:
        """Replace frame data with new version information."""
        return {ATTR_SENSORS: {ATTR_FRAME_VERSIONS: {frame: version}}}

    # Test with frame type that are handled during setup.
    sensor_data.data = _frame_version_data(frame_type, 1)
    ecomax.handle_frame(sensor_data)
    await ecomax.wait_until_done()
    mock_put_nowait.assert_not_called()

    # Test with same frame type after setup done.
    mock_put_nowait.reset_mock()
    sensor_data.data = _frame_version_data(frame_type, 2)
    with patch.object(EcoMAX, "data", {ATTR_SETUP: True}):
        ecomax.handle_frame(sensor_data)
        await ecomax.wait_until_done()

    mock_put_nowait.assert_called_once_with(frame_request)


@pytest.mark.parametrize("state", [STATE_ON, STATE_OFF])
async def test_ecomax_control(state: State, ecomax: EcoMAX, caplog) -> None:
    """Test ecoMAX control."""
    coro = getattr(ecomax, f"turn_{state}")
    await coro()
    assert "control is not available" in caplog.text
    switch = AsyncMock(spec=EcomaxSwitch)
    await ecomax.dispatch(ATTR_ECOMAX_CONTROL, switch)
    await coro()
    switch.set.assert_awaited_once_with(state, retries=0)


@pytest.mark.parametrize("state", [STATE_ON, STATE_OFF])
@patch("pyplumio.devices.ecomax.EcoMAX.create_task")
def test_ecomax_control_nowait(mock_create_task, ecomax: EcoMAX, state: State) -> None:
    """Test ecoMAX control without waiting for result."""
    func = getattr(ecomax, f"turn_{state}_nowait")
    with patch(
        f"pyplumio.devices.ecomax.EcoMAX.turn_{state}", new_callable=Mock
    ) as mock_coro:
        func()

    mock_coro.assert_called_once()
    mock_create_task.assert_called_once_with(mock_coro.return_value)


@patch("pyplumio.devices.mixer.Mixer.shutdown")
@patch("pyplumio.devices.thermostat.Thermostat.shutdown")
@patch("pyplumio.devices.Device.cancel_tasks")
@json_test_data("messages/sensor_data.json", selector="message")
async def test_ecomax_shutdown(
    mock_cancel_tasks,
    mock_thermostat_shutdown,
    mock_mixer_shutdown,
    ecomax: EcoMAX,
    sensor_data_message,
) -> None:
    """Test shutting down the ecoMAX and children tasks."""
    ecomax.handle_frame(SensorDataMessage(message=sensor_data_message))
    await ecomax.wait_until_done()

    with patch("pyplumio.devices.Device.wait_until_done") as mock_wait_until_done:
        await ecomax.shutdown()

    mock_wait_until_done.assert_awaited_once()
    mock_cancel_tasks.assert_called_once()
    mock_thermostat_shutdown.assert_awaited_once()
    mock_mixer_shutdown.assert_awaited_once()


@patch("pyplumio.devices.ecomax.EcoMAX.request")
@patch("pyplumio.devices.ecomax.EcoMAX.wait_for")
async def test_ecomax_setup(mock_wait_for, mock_request, ecomax: EcoMAX) -> None:
    """Test setting up an ecoMAX entry."""
    ecomax.dispatch_nowait(ATTR_SETUP, True)
    await ecomax.wait_until_done()
    assert ATTR_FRAME_ERRORS not in ecomax.data
    assert mock_request.await_count == len(REQUIRED)
    mock_wait_for.assert_awaited_once_with(ATTR_SENSORS, timeout=60.0)


@patch("pyplumio.devices.ecomax.EcoMAX.request")
@patch("pyplumio.devices.ecomax.EcoMAX.wait_for", side_effect=(asyncio.TimeoutError,))
async def test_ecomax_setup_failed(
    mock_wait_for, mock_request, ecomax: EcoMAX, caplog
) -> None:
    """Test setting up an ecoMAX entry with failure due to timeout."""
    ecomax.dispatch_nowait(ATTR_SETUP, True)
    await ecomax.wait_until_done()
    assert ecomax.get_nowait(ATTR_SETUP) is False
    assert "Could not setup device entry" in caplog.text
    assert "no response from device for 60 seconds" in caplog.text


@patch(
    "pyplumio.devices.ecomax.EcoMAX.request",
    side_effect=RequestError("test", FrameType.REQUEST_ALERTS),
)
@patch("pyplumio.devices.ecomax.EcoMAX.wait_for")
async def test_ecomax_setup_errors(mock_wait_for, mock_request, ecomax: EcoMAX) -> None:
    """Test setting up an ecoMAX entry with frame errors."""
    ecomax.dispatch_nowait(ATTR_SETUP, True)
    await ecomax.wait_until_done()
    assert FrameType.REQUEST_ALERTS in ecomax.get_nowait(ATTR_FRAME_ERRORS, [])
    assert mock_request.await_count == len(REQUIRED)
    mock_wait_for.assert_awaited_once_with(ATTR_SENSORS, timeout=60.0)


@patch("asyncio.Queue.put")
@class_from_json(
    EcomaxParametersResponse,
    "responses/ecomax_parameters.json",
    arguments=("message",),
)
async def test_ecomax_parameters_event_listener(
    mock_put, ecomax: EcoMAX, ecomax_parameters: EcomaxParametersResponse
) -> None:
    """Test event listener for ecoMAX parameters."""
    ecomax.handle_frame(ecomax_parameters)
    await ecomax.wait_until_done()
    fuzzy_logic = ecomax.get_nowait("fuzzy_logic")
    assert isinstance(fuzzy_logic, EcomaxSwitch)
    assert fuzzy_logic == STATE_ON
    assert fuzzy_logic.value == STATE_ON
    fuzzy_logic_request = await fuzzy_logic.create_request()
    assert isinstance(fuzzy_logic_request, SetEcomaxParameterRequest)
    assert fuzzy_logic_request.data == {
        ATTR_INDEX: 18,
        ATTR_VALUE: 1,
    }

    # Test that parameter instance is not recreated on subsequent calls.
    ecomax.handle_frame(ecomax_parameters)
    await ecomax.wait_until_done()
    assert ecomax.get_nowait("fuzzy_logic") is fuzzy_logic

    # Test parameter with the step (heating_heat_curve)
    fuel_calorific_value = ecomax.get_nowait("fuel_calorific_value")
    assert isinstance(fuel_calorific_value, EcomaxNumber)
    assert equal_parameter_value(fuel_calorific_value.value, 4.6)
    assert equal_parameter_value(fuel_calorific_value.min_value, 0.1)
    assert equal_parameter_value(fuel_calorific_value.max_value, 25.0)

    # Test setting parameter with the step.
    await fuel_calorific_value.set(2.5, timeout=0)
    request = mock_put.call_args[0][0]
    assert isinstance(request, SetEcomaxParameterRequest)
    assert request.data[ATTR_VALUE] == 25

    # Test parameter with the offset (heating_heat_curve_shift)
    heating_heat_curve_shift = ecomax.get_nowait("heating_curve_shift")
    assert isinstance(heating_heat_curve_shift, EcomaxNumber)
    assert equal_parameter_value(heating_heat_curve_shift.value, 0.0)
    assert equal_parameter_value(heating_heat_curve_shift.min_value, -20.0)
    assert equal_parameter_value(heating_heat_curve_shift.max_value, 20.0)
    assert heating_heat_curve_shift.unit_of_measurement == UnitOfMeasurement.CELSIUS

    # Test setting the parameter with the offset.
    await heating_heat_curve_shift.set(1, timeout=0)
    request = mock_put.call_args[0][0]
    assert isinstance(request, SetEcomaxParameterRequest)
    assert request.data[ATTR_VALUE] == 21


@class_from_json(
    EcomaxParametersResponse,
    "unknown/unknown_ecomax_parameter.json",
    arguments=("message",),
)
async def test_unknown_ecomax_parameter(
    ecomax: EcoMAX, caplog, unknown_ecomax_parameter: EcomaxParametersResponse
) -> None:
    """Test unknown ecoMAX parameter."""
    with caplog.at_level(logging.WARNING):
        ecomax.handle_frame(unknown_ecomax_parameter)
        await ecomax.wait_until_done()

    assert "unknown ecoMAX parameter (139)" in caplog.text
    assert "ParameterValues(value=1, min_value=1, max_value=1)" in caplog.text
    assert "ecoMAX 350P2-ZF" in caplog.text


@class_from_json(SensorDataMessage, "messages/sensor_data.json", arguments=("message",))
async def test_name_collisions(ecomax: EcoMAX, sensor_data: SensorDataMessage) -> None:
    """Test that the sensor names don't collide with the parameters."""
    ecomax.handle_frame(sensor_data)
    await ecomax.wait_until_done()
    for descriptions in PARAMETER_TYPES.values():
        collisions = [
            description.name
            for description in descriptions
            if description.name in ecomax.data
        ]
        assert not collisions, f"found collisions: {collisions}"


async def test_fuel_consumption_event_listener(
    frozen_time, caplog, ecomax: EcoMAX
) -> None:
    """Test event listener for fuel consumption."""
    frozen_time.tick(timedelta(seconds=10))
    ecomax.handle_frame(Response(data={ATTR_FUEL_CONSUMPTION: 3.6}))
    await ecomax.wait_until_done()
    fuel_burned = cast(float, ecomax.get_nowait(ATTR_FUEL_BURNED))
    assert equal_parameter_value(fuel_burned, 0.01)

    # Test with outdated data.
    message = "Skipping outdated fuel consumption"
    frozen_time.tick(timedelta(minutes=5, seconds=10))
    ecomax.handle_frame(Response(data={ATTR_FUEL_CONSUMPTION: 1}))
    await ecomax.wait_until_done()
    fuel_burned = cast(float, ecomax.get_nowait(ATTR_FUEL_BURNED))
    assert equal_parameter_value(fuel_burned, 0.01)
    assert message in caplog.text
    caplog.clear()

    frozen_time.tick(timedelta(seconds=10))
    ecomax.handle_frame(Response(data={ATTR_FUEL_CONSUMPTION: 7.2}))
    await ecomax.wait_until_done()
    assert message not in caplog.text
    fuel_burned = cast(float, ecomax.get_nowait(ATTR_FUEL_BURNED))
    assert equal_parameter_value(fuel_burned, 0.02)


@class_from_json(
    MixerParametersResponse,
    "responses/mixer_parameters.json",
    arguments=("message",),
)
async def test_mixer_parameters_event_listener(
    ecomax: EcoMAX, mixer_parameters: MixerParametersResponse
) -> None:
    """Test event listener for mixer parameters."""
    ecomax.handle_frame(mixer_parameters)
    await ecomax.wait_until_done()
    mixers = cast(dict[int, Mixer], ecomax.get_nowait(ATTR_MIXERS))
    assert isinstance(mixers, dict)
    assert len(mixers) == 1
    assert all(isinstance(mixer, Mixer) for mixer in mixers.values())


async def test_mixer_parameters_event_listener_without_mixers(ecomax: EcoMAX) -> None:
    """Test event listener for mixer parameters without mixers."""
    ecomax.handle_frame(MixerParametersResponse(data={ATTR_MIXER_PARAMETERS: {}}))
    await ecomax.wait_until_done()
    assert not ecomax.get_nowait(ATTR_MIXER_PARAMETERS, UNDEFINED)


@class_from_json(SensorDataMessage, "messages/sensor_data.json", arguments=("message",))
async def test_mixer_sensors_event_listener(
    ecomax: EcoMAX, sensor_data: SensorDataMessage
) -> None:
    """Test event listener for mixer sensors."""
    ecomax.handle_frame(sensor_data)
    await ecomax.wait_until_done()
    mixers = cast(dict[int, Mixer], ecomax.get_nowait(ATTR_MIXERS))
    assert isinstance(mixers, dict)
    assert len(mixers) == 1
    assert all(isinstance(mixer, Mixer) for mixer in mixers.values())
    assert ecomax.get_nowait(ATTR_MIXERS_AVAILABLE) == 5
    assert ecomax.get_nowait(ATTR_MIXERS_CONNECTED) == 1


async def test_mixer_sensors_callbacks_without_mixers(ecomax: EcoMAX) -> None:
    """Test event listener for mixer sensors without mixers."""
    ecomax.handle_frame(MixerParametersResponse(data={ATTR_MIXER_SENSORS: {}}))
    await ecomax.wait_until_done()
    assert ecomax.get_nowait(ATTR_MIXER_SENSORS, UNDEFINED) is False


@class_from_json(SensorDataMessage, "messages/sensor_data.json", arguments=("message",))
async def test_ecomax_sensors_event_listener(
    ecomax: EcoMAX, sensor_data: SensorDataMessage
) -> None:
    """Test event listener for ecoMAX sensors."""
    ecomax.handle_frame(sensor_data)
    await ecomax.wait_until_done()
    heating_target = cast(float, ecomax.get_nowait("heating_target"))
    assert equal_parameter_value(heating_target, 41.0)

    ecomax_control = ecomax.get_nowait(ATTR_ECOMAX_CONTROL)
    assert isinstance(ecomax_control, EcomaxSwitch)
    assert ecomax_control.value == STATE_OFF

    ecomax_control_request = await ecomax_control.create_request()
    assert isinstance(ecomax_control_request, EcomaxControlRequest)
    assert ecomax_control_request.data == {ATTR_VALUE: 0}

    # Check ecomax_control reference equility.
    sensor_data_message2 = SensorDataMessage(data={ATTR_STATE: DeviceState.WORKING})
    ecomax.handle_frame(sensor_data_message2)
    await ecomax.wait_until_done()
    ecomax_control2 = ecomax.get_nowait(ATTR_ECOMAX_CONTROL)
    assert isinstance(ecomax_control2, EcomaxSwitch)
    assert ecomax_control2 is ecomax_control
    assert ecomax_control2.value == STATE_ON
    ecomax_control2_request = await ecomax_control.create_request()
    assert ecomax_control2_request.data == {ATTR_VALUE: 1}


@class_from_json(
    ThermostatParametersResponse,
    "responses/thermostat_parameters.json",
    arguments=("message",),
)
async def test_thermostat_parameters_event_listener(
    ecomax: EcoMAX, thermostat_parameters: ThermostatParametersResponse
) -> None:
    """Test event listener for thermostat parameters."""
    await ecomax.dispatch(ATTR_THERMOSTATS_AVAILABLE, 3)
    ecomax.handle_frame(thermostat_parameters)
    await ecomax.wait_until_done()
    thermostats = cast(dict[int, Thermostat], ecomax.get_nowait(ATTR_THERMOSTATS))
    assert isinstance(thermostats, dict)
    assert len(thermostats) == 1
    assert all(
        isinstance(thermostat, Thermostat) for thermostat in thermostats.values()
    )


@class_from_json(
    ThermostatParametersResponse,
    "responses/thermostat_parameters.json",
    arguments=("message",),
)
async def test_thermostat_parameters_event_listener_without_thermostats(
    ecomax: EcoMAX, thermostat_parameters: ThermostatParametersResponse
) -> None:
    """Test event listener for thermostat parameters without any thermostats."""
    await ecomax.dispatch(ATTR_THERMOSTATS_AVAILABLE, 0)
    ecomax.handle_frame(thermostat_parameters)
    await ecomax.wait_until_done()
    assert ecomax.get_nowait(ATTR_THERMOSTAT_PARAMETERS, UNDEFINED) is False


@class_from_json(
    ThermostatParametersResponse,
    "responses/thermostat_parameters.json",
    arguments=("message",),
)
async def test_thermostat_profile_event_listener(
    ecomax: EcoMAX, thermostat_parameters: ThermostatParametersResponse
) -> None:
    """Test event listener for thermostat profile."""
    await ecomax.dispatch(ATTR_THERMOSTATS_AVAILABLE, 3)
    ecomax.handle_frame(thermostat_parameters)
    await ecomax.wait_until_done()
    thermostat_profile = ecomax.get_nowait(ATTR_THERMOSTAT_PROFILE)
    assert isinstance(thermostat_profile, EcomaxNumber)
    assert equal_parameter_value(thermostat_profile.value, 0.0)
    assert equal_parameter_value(thermostat_profile.min_value, 0.0)
    assert equal_parameter_value(thermostat_profile.max_value, 5.0)
    thermostat_profile_request = await thermostat_profile.create_request()
    assert isinstance(thermostat_profile_request, SetThermostatParameterRequest)
    assert thermostat_profile_request.data == {
        ATTR_INDEX: 0,
        ATTR_VALUE: 0,
        ATTR_OFFSET: 0,
        ATTR_SIZE: 1,
    }

    # Test when thermostat profile is none.
    ecomax.handle_frame(Response(data={ATTR_THERMOSTAT_PROFILE: None}))
    await ecomax.wait_until_done()
    assert ecomax.get_nowait(ATTR_THERMOSTAT_PROFILE, UNDEFINED) is None


@class_from_json(SensorDataMessage, "messages/sensor_data.json", arguments=("message",))
async def test_thermostat_sensors_event_listener(
    ecomax: EcoMAX, sensor_data: SensorDataMessage
) -> None:
    """Test event listener for thermostat sensors."""
    ecomax.handle_frame(sensor_data)
    await ecomax.wait_until_done()
    thermostats = cast(dict[int, Thermostat], ecomax.get_nowait(ATTR_THERMOSTATS))
    assert isinstance(thermostats, dict)
    assert len(thermostats) == 1
    assert all(
        isinstance(thermostat, Thermostat) for thermostat in thermostats.values()
    )
    assert ecomax.get_nowait(ATTR_THERMOSTATS_AVAILABLE) == 2
    assert ecomax.get_nowait(ATTR_THERMOSTATS_CONNECTED) == 1


async def test_thermostat_sensors_event_listener_without_thermostats(
    ecomax: EcoMAX,
) -> None:
    """Test event lister for thermostat sensors without thermostats."""
    ecomax.handle_frame(
        ThermostatParametersResponse(data={ATTR_THERMOSTAT_SENSORS: {}})
    )
    await ecomax.wait_until_done()
    assert ecomax.get_nowait(ATTR_THERMOSTAT_SENSORS, UNDEFINED) is False


@class_from_json(SchedulesResponse, "responses/schedules.json", arguments=("message",))
@json_test_data("responses/schedules.json", selector="data")
async def test_ecomax_schedules_event_listener(
    ecomax: EcoMAX, schedules: SchedulesResponse, schedules_data
) -> None:
    """Test event listener for schedules."""
    ecomax.handle_frame(schedules)
    await ecomax.wait_until_done()
    schedules_arg = cast(dict[str, Schedule], ecomax.get_nowait(ATTR_SCHEDULES))
    assert isinstance(schedules_arg, dict)
    assert len(schedules_arg) == 2
    heating_schedule = schedules_arg["heating"]
    assert isinstance(heating_schedule, Schedule)

    heating_schedule_switch = ecomax.get_nowait("heating_schedule_switch")
    assert isinstance(heating_schedule_switch, ScheduleSwitch)
    assert heating_schedule_switch.value == STATE_OFF

    water_heater_schedule_parameter = ecomax.get_nowait(
        "water_heater_schedule_parameter"
    )
    assert isinstance(water_heater_schedule_parameter, ScheduleNumber)
    assert water_heater_schedule_parameter.value == 5
    assert water_heater_schedule_parameter.min_value == 0
    assert water_heater_schedule_parameter.max_value == 30
    water_heater_schedule_parameter_request = (
        await water_heater_schedule_parameter.create_request()
    )
    assert isinstance(water_heater_schedule_parameter_request, SetScheduleRequest)
    assert water_heater_schedule_parameter_request.data == {
        ATTR_TYPE: "water_heater",
        ATTR_SWITCH: ecomax.data[f"water_heater_{ATTR_SCHEDULE_SWITCH}"],
        ATTR_PARAMETER: ecomax.data[f"water_heater_{ATTR_SCHEDULE_PARAMETER}"],
        ATTR_SCHEDULE: ecomax.data[ATTR_SCHEDULES]["water_heater"],
    }

    schedule_data = schedules_data[ATTR_SCHEDULES][0][1]
    for index, weekday in enumerate(
        (
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        )
    ):
        schedule = getattr(heating_schedule, weekday)
        assert (
            schedule.schedule
            == ScheduleDay.from_iterable(schedule_data[index]).schedule
        )

    # Test that parameter instance is not recreated on subsequent calls.
    ecomax.handle_frame(schedules)
    await ecomax.wait_until_done()
    assert ecomax.get_nowait("heating_schedule_switch") is heating_schedule_switch
