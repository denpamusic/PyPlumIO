"""Contains tests for devices."""

import asyncio
from typing import Dict
from unittest.mock import AsyncMock, Mock, call, patch
import warnings

import pytest

from pyplumio.const import (
    ATTR_DEVICE_INDEX,
    ATTR_INDEX,
    ATTR_LOADED,
    ATTR_OFFSET,
    ATTR_PARAMETER,
    ATTR_SCHEDULE,
    ATTR_SENSORS,
    ATTR_SWITCH,
    ATTR_TYPE,
    ATTR_VALUE,
    STATE_OFF,
    STATE_ON,
    DeviceType,
    FrameType,
)
from pyplumio.devices import Mixer, Thermostat, get_device_handler
from pyplumio.devices.ecomax import (
    ATTR_FUEL_BURNED,
    ATTR_MIXERS,
    ATTR_THERMOSTATS,
    DATA_FRAME_TYPES,
    EcoMAX,
)
from pyplumio.devices.ecoster import EcoSTER
from pyplumio.exceptions import ParameterNotFoundError, UnknownDeviceError
from pyplumio.frames import Response
from pyplumio.frames.messages import RegulatorDataMessage, SensorDataMessage
from pyplumio.frames.requests import (
    AlertsRequest,
    DataSchemaRequest,
    EcomaxControlRequest,
    SchedulesRequest,
    SetEcomaxParameterRequest,
    SetMixerParameterRequest,
    SetScheduleRequest,
    SetThermostatParameterRequest,
    UIDRequest,
)
from pyplumio.frames.responses import (
    DataSchemaResponse,
    EcomaxParametersResponse,
    MixerParametersResponse,
    SchedulesResponse,
    ThermostatParametersResponse,
)
from pyplumio.helpers.network_info import NetworkInfo
from pyplumio.helpers.schedule import Schedule
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures.ecomax_parameters import (
    ATTR_ECOMAX_CONTROL,
    EcomaxBinaryParameter,
)
from pyplumio.structures.frame_versions import ATTR_FRAME_VERSIONS
from pyplumio.structures.fuel_consumption import ATTR_FUEL_CONSUMPTION
from pyplumio.structures.mixer_parameters import (
    ATTR_MIXER_PARAMETERS,
    MixerBinaryParameter,
    MixerParameter,
)
from pyplumio.structures.regulator_data import ATTR_REGDATA
from pyplumio.structures.schedules import (
    ATTR_SCHEDULE_PARAMETER,
    ATTR_SCHEDULE_SWITCH,
    ATTR_SCHEDULES,
    ScheduleBinaryParameter,
    ScheduleParameter,
)
from pyplumio.structures.thermostat_parameters import (
    ATTR_THERMOSTAT_PARAMETERS,
    ATTR_THERMOSTAT_PROFILE,
    ThermostatParameter,
)
from pyplumio.structures.thermostat_sensors import ATTR_THERMOSTAT_COUNT

UNKNOWN_DEVICE: int = 99
UNKNOWN_FRAME: int = 99


def test_device_handler() -> None:
    """Test getting device handler class by device address."""
    cls = get_device_handler(DeviceType.ECOMAX)
    assert cls == "devices.ecomax.EcoMAX"
    with pytest.raises(UnknownDeviceError):
        cls = get_device_handler(UNKNOWN_DEVICE)


def test_ecoster(ecoster: EcoSTER) -> None:
    """Test ecoster instance."""
    assert isinstance(ecoster, EcoSTER)


@patch(
    "pyplumio.devices.ecomax.EcoMAX.make_request",
    side_effect=(ValueError("test"), True, True, True, True, True, True, True),
)
async def test_request_data_frames(mock_make_request, caplog) -> None:
    """Test requesting initial data frames."""
    ecomax = EcoMAX(asyncio.Queue(), network=NetworkInfo())
    ecomax.set_device_data(ATTR_LOADED, True)
    await ecomax.wait_until_done()
    assert "Request failed: test" in caplog.text
    assert mock_make_request.await_count == len(DATA_FRAME_TYPES)


@patch("asyncio.Queue.put_nowait")
async def test_frame_versions_update(
    mock_put_nowait, ecomax: EcoMAX, messages: Dict[int, bytearray]
) -> None:
    """Test requesting updated frames."""
    ecomax.handle_frame(
        SensorDataMessage(message=messages[FrameType.MESSAGE_SENSOR_DATA])
    )
    await ecomax.wait_until_done()
    mock_put_nowait.assert_has_calls(
        [
            call(DataSchemaRequest(recipient=DeviceType.ECOMAX)),
            call(SchedulesRequest(recipient=DeviceType.ECOMAX)),
            call(UIDRequest(recipient=DeviceType.ECOMAX)),
            call(AlertsRequest(recipient=DeviceType.ECOMAX)),
        ]
    )


async def test_ecomax_data_callbacks(
    ecomax: EcoMAX, messages: Dict[int, bytearray]
) -> None:
    """Test callbacks that are fired on received data frames."""
    ecomax.handle_frame(
        SensorDataMessage(message=messages[FrameType.MESSAGE_SENSOR_DATA])
    )
    await ecomax.wait_until_done()
    heating_target = await ecomax.get_value("heating_target")
    assert heating_target == 41.0

    ecomax_control = await ecomax.get_parameter(ATTR_ECOMAX_CONTROL)
    assert isinstance(ecomax_control, EcomaxBinaryParameter)
    assert isinstance(ecomax_control.request, EcomaxControlRequest)
    assert ecomax_control.value == STATE_OFF
    assert ecomax_control.request.data == {ATTR_VALUE: 0}


async def test_ecomax_parameters_callbacks(
    ecomax: EcoMAX, messages: Dict[int, bytearray]
) -> None:
    """Test callbacks that are fired on received parameter frames."""
    ecomax.handle_frame(
        EcomaxParametersResponse(message=messages[FrameType.RESPONSE_ECOMAX_PARAMETERS])
    )
    assert ecomax.wait_until_done()
    fuzzy_logic = await ecomax.get_parameter("fuzzy_logic")
    assert isinstance(fuzzy_logic, EcomaxBinaryParameter)
    assert isinstance(fuzzy_logic.request, SetEcomaxParameterRequest)
    assert fuzzy_logic.value == STATE_ON
    fuzzy_logic_value = await ecomax.get_value("fuzzy_logic")
    assert fuzzy_logic_value == STATE_ON
    assert fuzzy_logic.request.data == {
        ATTR_INDEX: 18,
        ATTR_VALUE: 1,
    }

    airflow_power_50 = await ecomax.get_parameter("airflow_power_50")
    assert airflow_power_50.value == 60.0
    assert airflow_power_50.min_value == 41.0
    assert airflow_power_50.max_value == 60.0


@patch("time.time", side_effect=(0, 10, 600, 610))
async def test_fuel_consumption_callbacks(mock_time, caplog) -> None:
    """Test callbacks that are fired on received fuel consumption."""
    ecomax = EcoMAX(asyncio.Queue(), network=NetworkInfo())
    ecomax.handle_frame(Response(data={ATTR_FUEL_CONSUMPTION: 3.6}))
    await ecomax.wait_until_done()
    fuel_burned = await ecomax.get_value(ATTR_FUEL_BURNED)
    assert fuel_burned == 0.01
    ecomax.handle_frame(Response(data={ATTR_FUEL_CONSUMPTION: 1}))
    await ecomax.wait_until_done()
    assert "Skipping outdated fuel consumption" in caplog.text


async def test_regdata_callbacks(
    ecomax: EcoMAX, messages: Dict[int, bytearray]
) -> None:
    """Test callbacks that are fired on received regdata."""
    ecomax.handle_frame(
        DataSchemaResponse(message=messages[FrameType.RESPONSE_DATA_SCHEMA])
    )
    ecomax.handle_frame(
        RegulatorDataMessage(message=messages[FrameType.MESSAGE_REGULATOR_DATA])
    )
    await ecomax.wait_until_done()
    regdata = await ecomax.get_value(ATTR_REGDATA)
    assert regdata[1792] == 0
    assert round(regdata[1024], 1) == 22.4
    assert regdata[1280] == 41
    assert regdata[183] == "0.0.0.0"
    assert regdata[184] == "255.255.255.0"


async def test_regdata_callbacks_without_schema(
    ecomax: EcoMAX, messages: Dict[int, bytearray]
) -> None:
    """Test callbacks that are fired on received regdata."""
    ecomax.handle_frame(
        RegulatorDataMessage(message=messages[FrameType.MESSAGE_REGULATOR_DATA])
    )
    await ecomax.wait_until_done()
    assert ATTR_FRAME_VERSIONS in ecomax.data
    assert ATTR_REGDATA not in ecomax.data


async def test_mixer_sensors_callbacks(
    ecomax: EcoMAX, messages: Dict[int, bytearray]
) -> None:
    """Test callbacks that are fired on receiving mixer sensors info."""
    ecomax.handle_frame(
        SensorDataMessage(message=messages[FrameType.MESSAGE_SENSOR_DATA])
    )
    assert ecomax.wait_until_done()
    mixers = await ecomax.get_value(ATTR_MIXERS)
    assert len(mixers) == 1
    mixer = mixers[4]
    assert isinstance(mixer, Mixer)
    assert mixer.index == 4
    assert mixer.data == {"current_temp": 20.0, "target_temp": 40, "pump": False}


async def test_thermostat_sensors_callbacks(
    ecomax: EcoMAX, messages: Dict[int, bytearray]
) -> None:
    """Test callbacks that are fired on receiving thermostat sensors info."""
    ecomax.handle_frame(
        SensorDataMessage(message=messages[FrameType.MESSAGE_SENSOR_DATA])
    )
    assert ecomax.wait_until_done()
    thermostats = await ecomax.get_value(ATTR_THERMOSTATS)
    assert len(thermostats) == 1
    thermostat = thermostats[0]
    assert isinstance(thermostat, Thermostat)
    assert thermostat.index == 0
    assert thermostat.data == {
        "state": 3,
        "current_temp": 43.5,
        "target_temp": 50.0,
        "contacts": True,
        "schedule": False,
    }
    thermostat_count = await ecomax.get_value(ATTR_THERMOSTAT_COUNT)
    assert thermostat_count == 1


async def test_thermostat_parameters_callbacks(
    ecomax: EcoMAX, messages: Dict[int, bytearray]
) -> None:
    """Test callbacks that are fired on receiving thermostat parameters."""
    ecomax.handle_frame(Response(data={ATTR_THERMOSTAT_COUNT: 3}))
    ecomax.handle_frame(
        ThermostatParametersResponse(
            message=messages[FrameType.RESPONSE_THERMOSTAT_PARAMETERS]
        )
    )
    await ecomax.wait_until_done()
    thermostats = await ecomax.get_value(ATTR_THERMOSTATS)
    assert len(thermostats) == 1
    thermostat = thermostats[0]
    assert len(thermostat.data) == 12
    party_target_temp = await thermostat.get_parameter("party_target_temp")
    assert isinstance(party_target_temp, ThermostatParameter)
    assert isinstance(party_target_temp.request, SetThermostatParameterRequest)
    assert isinstance(party_target_temp.device, Thermostat)
    assert party_target_temp.value == 22.0
    assert party_target_temp.min_value == 10.0
    assert party_target_temp.max_value == 35.0
    assert party_target_temp.offset == 0
    assert party_target_temp.request.data == {
        ATTR_INDEX: 2,
        ATTR_VALUE: 220,
        ATTR_OFFSET: 0,
    }


async def test_thermostat_parameters_callbacks_without_thermostats(
    ecomax: EcoMAX, messages: Dict[int, bytearray]
) -> None:
    """Test callbacks that are fired on receiving thermostat parameters
    without any thermostats."""
    ecomax.handle_frame(Response(data={ATTR_THERMOSTAT_COUNT: 0}))
    ecomax.handle_frame(
        ThermostatParametersResponse(
            message=messages[FrameType.RESPONSE_THERMOSTAT_PARAMETERS]
        )
    )
    await ecomax.wait_until_done()
    assert not await ecomax.get_value(ATTR_THERMOSTAT_PARAMETERS)
    thermostat_profile = await ecomax.get_value(ATTR_THERMOSTAT_PROFILE)
    assert thermostat_profile is None


async def test_thermostat_profile_callbacks(
    ecomax: EcoMAX, messages: Dict[int, bytearray]
) -> None:
    """Test callbacks that are fired on receiving thermostat profile."""
    ecomax.handle_frame(Response(data={ATTR_THERMOSTAT_COUNT: 3}))
    ecomax.handle_frame(
        ThermostatParametersResponse(
            message=messages[FrameType.RESPONSE_THERMOSTAT_PARAMETERS]
        )
    )
    await ecomax.wait_until_done()
    thermostat_profile = await ecomax.get_parameter(ATTR_THERMOSTAT_PROFILE)
    assert thermostat_profile.value == 0.0
    assert thermostat_profile.min_value == 0.0
    assert thermostat_profile.max_value == 5.0
    assert isinstance(thermostat_profile.request, SetThermostatParameterRequest)
    assert thermostat_profile.request.data == {
        ATTR_INDEX: 0,
        ATTR_VALUE: 0,
        ATTR_OFFSET: 0,
    }

    # Test when thermostat profile is none.
    ecomax.handle_frame(Response(data={ATTR_THERMOSTAT_PROFILE: None}))
    await ecomax.wait_until_done()
    assert await ecomax.get_value(ATTR_THERMOSTAT_PROFILE) is None


async def test_mixer_parameters_callbacks(
    ecomax: EcoMAX, messages: Dict[int, bytearray]
) -> None:
    """Test callbacks that are fired on receiving mixer parameters."""
    ecomax.handle_frame(
        MixerParametersResponse(message=messages[FrameType.RESPONSE_MIXER_PARAMETERS])
    )
    await ecomax.wait_until_done()
    mixers = await ecomax.get_value(ATTR_MIXERS)
    assert len(mixers) == 1
    mixer = mixers[0]
    assert len(mixer.data) == 6
    mixer_target_temp = await mixer.get_parameter("mixer_target_temp")
    assert isinstance(mixer_target_temp, MixerParameter)
    assert isinstance(mixer_target_temp.request, SetMixerParameterRequest)
    assert isinstance(mixer_target_temp.device, Mixer)
    assert mixer_target_temp.value == 40.0
    assert mixer_target_temp.min_value == 30.0
    assert mixer_target_temp.max_value == 60.0
    assert mixer_target_temp.request.data == {
        ATTR_INDEX: 0,
        ATTR_VALUE: 40,
        ATTR_DEVICE_INDEX: 0,
    }

    weather_control = await mixer.get_parameter("weather_control")
    assert isinstance(weather_control, MixerBinaryParameter)
    assert weather_control.value == STATE_ON

    heat_curve = await mixer.get_parameter("heat_curve")
    assert isinstance(heat_curve, MixerParameter)
    assert heat_curve.value == 1.3
    assert heat_curve.min_value == 1.0
    assert heat_curve.max_value == 3.0


async def test_mixer_parameters_callbacks_without_mixers(ecomax: EcoMAX) -> None:
    """Test mixer parameters callbacks without any mixers."""
    ecomax.handle_frame(MixerParametersResponse(data={ATTR_MIXER_PARAMETERS: None}))
    await ecomax.wait_until_done()
    assert not await ecomax.get_value(ATTR_MIXER_PARAMETERS)


async def test_schedule_callback(
    ecomax: EcoMAX, messages: Dict[int, bytearray], data: Dict[int, DeviceDataType]
) -> None:
    """Test callback that is fired on receiving schedule data."""
    ecomax.handle_frame(
        SchedulesResponse(message=messages[FrameType.RESPONSE_SCHEDULES])
    )
    schedules = await ecomax.get_value(ATTR_SCHEDULES)
    assert len(schedules) == 1
    heating_schedule = schedules["heating"]
    assert isinstance(heating_schedule, Schedule)

    heating_schedule_switch = await ecomax.get_parameter("heating_schedule_switch")
    assert heating_schedule_switch.value == STATE_OFF
    assert isinstance(heating_schedule_switch, ScheduleBinaryParameter)

    heating_schedule_parameter = await ecomax.get_parameter(
        "heating_schedule_parameter"
    )
    assert isinstance(heating_schedule_parameter, ScheduleParameter)
    assert isinstance(heating_schedule_parameter.request, SetScheduleRequest)
    assert heating_schedule_parameter.value == 5
    assert heating_schedule_parameter.min_value == 0
    assert heating_schedule_parameter.max_value == 30
    assert heating_schedule_parameter.request.data == {
        ATTR_TYPE: "heating",
        ATTR_SWITCH: ecomax.data[f"heating_{ATTR_SCHEDULE_SWITCH}"],
        ATTR_PARAMETER: ecomax.data[f"heating_{ATTR_SCHEDULE_PARAMETER}"],
        ATTR_SCHEDULE: ecomax.data[ATTR_SCHEDULES]["heating"],
    }

    schedule_data = data[FrameType.RESPONSE_SCHEDULES][ATTR_SCHEDULES][0][1]
    for index, weekday in enumerate(
        ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
    ):
        schedule = getattr(heating_schedule, weekday)
        assert schedule.intervals == schedule_data[index]


async def test_subscribe(ecomax: EcoMAX, messages: Dict[int, bytearray]) -> None:
    """Test callback registration."""
    mock_callback = AsyncMock(return_value=None)
    ecomax.subscribe("heating_target", mock_callback)
    ecomax.handle_frame(
        SensorDataMessage(message=messages[FrameType.MESSAGE_SENSOR_DATA])
    )
    await ecomax.wait_until_done()
    mock_callback.assert_awaited_once_with(41)
    mock_callback.reset_mock()

    # Test with change.
    ecomax.handle_frame(Response(data={ATTR_SENSORS: {"heating_target": 45}}))
    await ecomax.wait_until_done()
    mock_callback.assert_awaited_once_with(45)
    mock_callback.reset_mock()

    # Remove the callback and make sure it doesn't fire again.
    ecomax.unsubscribe("heating_target", mock_callback)
    ecomax.handle_frame(Response(data={ATTR_SENSORS: {"heating_target": 50}}))
    await ecomax.wait_until_done()
    mock_callback.assert_not_awaited()


async def test_get_value(ecomax: EcoMAX) -> None:
    """Test getting the value from device data."""
    mock_event = Mock(spec=asyncio.Event)
    with pytest.raises(KeyError), patch(
        "pyplumio.devices.Device.create_event", return_value=mock_event
    ) as mock_create_event:
        mock_event.wait = AsyncMock()
        await ecomax.get_value("foo")

    mock_create_event.assert_called_once_with("foo")
    mock_event.wait.assert_awaited_once()


@patch(
    "pyplumio.devices.ecomax.EcoMAX.get_value",
    side_effect=(asyncio.TimeoutError, True),
)
@patch("asyncio.Queue.put_nowait")
async def test_make_request(
    mock_put_nowait, mock_get_value, bypass_asyncio_sleep, ecomax: EcoMAX
) -> None:
    """Test requesting the value."""
    assert await ecomax.make_request("foo", FrameType.REQUEST_ALERTS, timeout=5)
    mock_get_value.assert_awaited_with("foo", timeout=5)
    assert mock_put_nowait.call_count == 2
    args, _ = mock_put_nowait.call_args
    assert isinstance(args[0], AlertsRequest)


@patch(
    "pyplumio.devices.ecomax.EcoMAX.get_value",
    side_effect=(asyncio.TimeoutError, asyncio.TimeoutError),
)
async def test_make_request_error(
    mock_get_value, bypass_asyncio_sleep, ecomax: EcoMAX
) -> None:
    """Test requesting the value with error."""
    with pytest.raises(ValueError):
        await ecomax.make_request("foo", FrameType.REQUEST_ALERTS, retries=1)


@patch("pyplumio.helpers.parameter.Parameter.is_changed", False)
async def test_set_value(ecomax: EcoMAX, messages: Dict[int, bytearray]) -> None:
    """Test setting parameter value via set_value helper."""
    ecomax.handle_frame(
        EcomaxParametersResponse(message=messages[FrameType.RESPONSE_ECOMAX_PARAMETERS])
    )
    ecomax.handle_frame(Response(data={ATTR_THERMOSTAT_COUNT: 3}))
    ecomax.handle_frame(
        ThermostatParametersResponse(
            message=messages[FrameType.RESPONSE_THERMOSTAT_PARAMETERS]
        )
    )
    ecomax.handle_frame(
        MixerParametersResponse(message=messages[FrameType.RESPONSE_MIXER_PARAMETERS])
    )
    assert ecomax.wait_until_done()

    # Test setting an ecomax parameter.
    assert await ecomax.set_value("fuel_flow_kg_h", 13.0)
    fuel_flow_kg_h = await ecomax.get_value("fuel_flow_kg_h")
    assert fuel_flow_kg_h == 13.0

    # Test setting an ecomax parameter without blocking.
    with patch(
        "pyplumio.helpers.task_manager.TaskManager.create_task"
    ) as mock_create_task:
        await ecomax.set_value_nowait("fuel_flow_kg_h", 10)
        mock_create_task.assert_called_once()

    # Test deprication warning on the await_confirmation binary flag.
    with warnings.catch_warnings(record=True) as warn:
        warnings.simplefilter("always")
        assert await ecomax.set_value("fuel_flow_kg_h", 13.0, await_confirmation=False)
        assert len(warn) == 1
        assert issubclass(warn[-1].category, DeprecationWarning)
        assert "deprecated" in str(warn[-1].message)

    # Test setting a thermostat parameter.
    thermostat = ecomax.data[ATTR_THERMOSTATS][0]
    assert await thermostat.set_value("party_target_temp", 21.0)
    target_party_temp = await thermostat.get_value("party_target_temp")
    assert target_party_temp == 21.0

    # Test setting a mixer parameter.
    mixer = ecomax.data[ATTR_MIXERS][0]
    assert await mixer.set_value("mixer_target_temp", 35.0)
    mixer_target_temp = await mixer.get_value("mixer_target_temp")
    assert mixer_target_temp == 35.0

    # Test with invalid parameter.
    ecomax.data["bar"] = Mock()
    with pytest.raises(ParameterNotFoundError):
        await ecomax.set_value("bar", 1)


async def test_get_parameter(ecomax: EcoMAX) -> None:
    """Test getting parameter from device."""
    mock_event = Mock(spec=asyncio.Event)
    with pytest.raises(KeyError), patch(
        "pyplumio.devices.Device.create_event", return_value=mock_event
    ) as mock_create_event:
        mock_event.wait = AsyncMock()
        await ecomax.get_parameter("foo")

    mock_create_event.assert_called_once_with("foo")
    mock_event.wait.assert_awaited_once()

    # Test with invalid parameter.
    ecomax.data["bar"] = Mock()
    with pytest.raises(ParameterNotFoundError):
        await ecomax.get_parameter("bar")


async def test_turn_on_off(ecomax: EcoMAX, caplog) -> None:
    """Test turning the controller on/off."""
    # Test turning on.
    assert not await ecomax.turn_on()
    assert "ecoMAX control is not available" in caplog.text
    ecomax.data[ATTR_ECOMAX_CONTROL] = AsyncMock()
    assert await ecomax.turn_on()
    ecomax.data[ATTR_ECOMAX_CONTROL].turn_on.assert_awaited_once()

    # Test turning off.
    del ecomax.data[ATTR_ECOMAX_CONTROL]
    await ecomax.turn_off()
    assert "ecoMAX control is not available" in caplog.text
    ecomax.data[ATTR_ECOMAX_CONTROL] = AsyncMock()
    await ecomax.turn_off()
    ecomax.data[ATTR_ECOMAX_CONTROL].turn_off.assert_awaited_once()


@patch("pyplumio.devices.Mixer.shutdown")
@patch("pyplumio.devices.Thermostat.shutdown")
@patch("pyplumio.devices.Device.cancel_tasks")
@patch("pyplumio.devices.Device.wait_until_done")
async def test_shutdown(
    mock_wait_until_done,
    mock_cancel_tasks,
    mock_thermostat_shutdown,
    mock_mixer_shutdown,
    ecomax: EcoMAX,
    messages: Dict[int, bytearray],
) -> None:
    """Test device tasks shutdown."""
    ecomax.handle_frame(
        SensorDataMessage(message=messages[FrameType.MESSAGE_SENSOR_DATA])
    )
    await ecomax.get_value(ATTR_MIXERS)
    await ecomax.get_value(ATTR_THERMOSTATS)
    await ecomax.shutdown()
    mock_wait_until_done.assert_awaited_once()
    mock_cancel_tasks.assert_called_once()
    mock_thermostat_shutdown.assert_awaited_once()
    mock_mixer_shutdown.assert_awaited_once()
