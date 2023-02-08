"""Contains tests for devices."""

import asyncio
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
    ATTR_SIZE,
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
from pyplumio.helpers.parameter import Parameter
from pyplumio.helpers.schedule import Schedule
from pyplumio.helpers.typing import EventDataType
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


@pytest.fixture(name="ecoster")
def fixture_ecoster() -> EcoSTER:
    """Return instance of ecoster."""
    return EcoSTER(asyncio.Queue(), network=NetworkInfo())


def test_device_handler() -> None:
    """Test getting device handler class by device address."""
    cls = get_device_handler(DeviceType.ECOMAX)
    assert cls == "devices.ecomax.EcoMAX"
    with pytest.raises(UnknownDeviceError):
        cls = get_device_handler(UNKNOWN_DEVICE)


def test_ecoster(ecoster: EcoSTER) -> None:
    """Test ecoster instance."""
    assert isinstance(ecoster, EcoSTER)


async def test_deprecated_get_value(ecomax: EcoMAX) -> None:
    """Test deprecated get_value method."""
    mock_parameter = Mock(spec=Parameter)
    with patch(
        "pyplumio.devices.Device.get",
        new_callable=AsyncMock,
        side_effect=(None, mock_parameter),
    ) as mock_get, warnings.catch_warnings(record=True) as warn:
        warnings.simplefilter("always")
        assert await ecomax.get_value("test") is None
        assert await ecomax.get_value("test") == mock_parameter.value
        assert len(warn) == 2
        assert issubclass(warn[-1].category, DeprecationWarning)
        assert "deprecated" in str(warn[-1].message)
        mock_get.assert_any_await("test", None)


async def test_deprecated_get_parameter(ecomax: EcoMAX) -> None:
    """Test deprecated get_parameter method."""
    with patch(
        "pyplumio.devices.Device.get", new_callable=AsyncMock
    ) as mock_get, warnings.catch_warnings(record=True) as warn:
        warnings.simplefilter("always")
        await ecomax.get_parameter("test")
        assert len(warn) == 1
        assert issubclass(warn[-1].category, DeprecationWarning)
        assert "deprecated" in str(warn[-1].message)
        mock_get.assert_awaited_once_with("test", None)


async def test_deprecated_set_value(ecomax: EcoMAX) -> None:
    """Test deprecated set_value method."""
    with patch(
        "pyplumio.devices.Device.set", new_callable=AsyncMock
    ) as mock_set, warnings.catch_warnings(record=True) as warn:
        warnings.simplefilter("always")
        await ecomax.set_value("test", 1)
        assert len(warn) == 1
        assert issubclass(warn[-1].category, DeprecationWarning)
        assert "deprecated" in str(warn[-1].message)
        mock_set.assert_awaited_once_with("test", 1, None)


def test_deprecated_set_value_nowait(ecomax: EcoMAX) -> None:
    """Test deprecated set_value_nowait method."""
    with patch(
        "pyplumio.devices.Device.set_nowait"
    ) as mock_set_nowait, warnings.catch_warnings(record=True) as warn:
        warnings.simplefilter("always")
        ecomax.set_value_nowait("test", 1)
        assert len(warn) == 1
        assert issubclass(warn[-1].category, DeprecationWarning)
        assert "deprecated" in str(warn[-1].message)
        mock_set_nowait.assert_called_once_with("test", 1, None)


async def test_async_setup() -> None:
    """Test requesting initial data frames."""
    ecomax = EcoMAX(asyncio.Queue(), network=NetworkInfo())

    with patch("pyplumio.devices.ecomax.EcoMAX.wait_for"), patch(
        "pyplumio.devices.ecomax.EcoMAX.request",
        side_effect=(True, True, True, True, True, True, True, True),
    ) as mock_request:
        await ecomax.async_setup()
        await ecomax.wait_until_done()

    assert await ecomax.get(ATTR_LOADED)
    assert mock_request.await_count == len(DATA_FRAME_TYPES)


async def test_async_setup_error(caplog) -> None:
    """Test with error during requesting initial data frames."""
    ecomax = EcoMAX(asyncio.Queue(), network=NetworkInfo())

    with patch("pyplumio.devices.ecomax.EcoMAX.wait_for"), patch(
        "pyplumio.devices.ecomax.EcoMAX.request",
        side_effect=(ValueError("test"), True, True, True, True, True, True, True),
    ) as mock_request:
        await ecomax.async_setup()
        await ecomax.wait_until_done()

    assert "Request failed" in caplog.text
    assert not await ecomax.get(ATTR_LOADED)
    assert mock_request.await_count == len(DATA_FRAME_TYPES)


async def test_frame_versions_update(
    ecomax: EcoMAX, messages: dict[FrameType, bytearray]
) -> None:
    """Test requesting updated frames."""
    with patch("asyncio.Queue.put_nowait") as mock_put_nowait:
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
    ecomax: EcoMAX, messages: dict[FrameType, bytearray]
) -> None:
    """Test callbacks that are dispatchd on received data frames."""
    ecomax.handle_frame(
        SensorDataMessage(message=messages[FrameType.MESSAGE_SENSOR_DATA])
    )
    await ecomax.wait_until_done()
    heating_target = await ecomax.get("heating_target")
    assert heating_target == 41.0

    ecomax_control = await ecomax.get(ATTR_ECOMAX_CONTROL)
    assert isinstance(ecomax_control, EcomaxBinaryParameter)
    assert isinstance(ecomax_control.request, EcomaxControlRequest)
    assert ecomax_control.value == STATE_OFF
    assert ecomax_control.request.data == {ATTR_VALUE: 0}


async def test_ecomax_parameters_callbacks(
    ecomax: EcoMAX, messages: dict[FrameType, bytearray]
) -> None:
    """Test callbacks that are dispatchd on received parameter frames."""
    ecomax.handle_frame(
        EcomaxParametersResponse(message=messages[FrameType.RESPONSE_ECOMAX_PARAMETERS])
    )
    await ecomax.wait_until_done()
    fuzzy_logic = await ecomax.get("fuzzy_logic")
    assert isinstance(fuzzy_logic, EcomaxBinaryParameter)
    assert isinstance(fuzzy_logic.request, SetEcomaxParameterRequest)
    assert fuzzy_logic.value == STATE_ON
    fuzzy_logic_value = await ecomax.get("fuzzy_logic")
    assert fuzzy_logic_value == STATE_ON
    assert fuzzy_logic.request.data == {
        ATTR_INDEX: 18,
        ATTR_VALUE: 1,
    }

    airflow_power_50 = await ecomax.get("airflow_power_50")
    assert airflow_power_50.value == 60.0
    assert airflow_power_50.min_value == 41.0
    assert airflow_power_50.max_value == 60.0


@patch("time.time", side_effect=(0, 10, 600, 610))
async def test_fuel_consumption_callbacks(mock_time, caplog) -> None:
    """Test callbacks that are dispatchd on received fuel consumption."""
    ecomax = EcoMAX(asyncio.Queue(), network=NetworkInfo())
    ecomax.handle_frame(Response(data={ATTR_FUEL_CONSUMPTION: 3.6}))
    await ecomax.wait_until_done()
    fuel_burned = await ecomax.get(ATTR_FUEL_BURNED)
    assert fuel_burned == 0.01
    ecomax.handle_frame(Response(data={ATTR_FUEL_CONSUMPTION: 1}))
    await ecomax.wait_until_done()
    assert "Skipping outdated fuel consumption" in caplog.text


async def test_regdata_callbacks(
    ecomax: EcoMAX, messages: dict[FrameType, bytearray]
) -> None:
    """Test callbacks that are dispatchd on received regdata."""
    ecomax.handle_frame(
        DataSchemaResponse(message=messages[FrameType.RESPONSE_DATA_SCHEMA])
    )
    ecomax.handle_frame(
        RegulatorDataMessage(message=messages[FrameType.MESSAGE_REGULATOR_DATA])
    )
    await ecomax.wait_until_done()
    regdata = await ecomax.get(ATTR_REGDATA)
    assert regdata[1792] == 0
    assert round(regdata[1024], 1) == 22.4
    assert regdata[1280] == 41
    assert regdata[183] == "0.0.0.0"
    assert regdata[184] == "255.255.255.0"


async def test_regdata_callbacks_without_schema(
    ecomax: EcoMAX, messages: dict[FrameType, bytearray]
) -> None:
    """Test callbacks that are dispatchd on received regdata."""
    ecomax.handle_frame(
        RegulatorDataMessage(message=messages[FrameType.MESSAGE_REGULATOR_DATA])
    )
    await ecomax.wait_until_done()
    assert ATTR_FRAME_VERSIONS in ecomax.data
    assert ATTR_REGDATA not in ecomax.data


async def test_mixer_sensors_callbacks(
    ecomax: EcoMAX, messages: dict[FrameType, bytearray]
) -> None:
    """Test callbacks that are dispatchd on receiving mixer sensors info."""
    ecomax.handle_frame(
        SensorDataMessage(message=messages[FrameType.MESSAGE_SENSOR_DATA])
    )
    await ecomax.wait_until_done()
    mixers = await ecomax.get(ATTR_MIXERS)
    assert len(mixers) == 1
    mixer = mixers[4]
    assert isinstance(mixer, Mixer)
    assert mixer.index == 4
    assert mixer.data == {"current_temp": 20.0, "target_temp": 40, "pump": False}


async def test_thermostat_sensors_callbacks(
    ecomax: EcoMAX, messages: dict[FrameType, bytearray]
) -> None:
    """Test callbacks that are dispatchd on receiving thermostat sensors info."""
    ecomax.handle_frame(
        SensorDataMessage(message=messages[FrameType.MESSAGE_SENSOR_DATA])
    )
    await ecomax.wait_until_done()
    thermostats = await ecomax.get(ATTR_THERMOSTATS)
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
    thermostat_count = await ecomax.get(ATTR_THERMOSTAT_COUNT)
    assert thermostat_count == 1


async def test_thermostat_parameters_callbacks(
    ecomax: EcoMAX, messages: dict[FrameType, bytearray]
) -> None:
    """Test callbacks that are dispatchd on receiving thermostat parameters."""
    ecomax.handle_frame(Response(data={ATTR_THERMOSTAT_COUNT: 3}))
    ecomax.handle_frame(
        ThermostatParametersResponse(
            message=messages[FrameType.RESPONSE_THERMOSTAT_PARAMETERS]
        )
    )
    await ecomax.wait_until_done()
    thermostats = await ecomax.get(ATTR_THERMOSTATS)
    assert len(thermostats) == 1
    thermostat = thermostats[0]
    assert len(thermostat.data) == 12
    party_target_temp = await thermostat.get("party_target_temp")
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
        ATTR_SIZE: 2,
    }


async def test_thermostat_parameters_callbacks_without_thermostats(
    ecomax: EcoMAX, messages: dict[FrameType, bytearray]
) -> None:
    """Test callbacks that are dispatchd on receiving thermostat parameters
    without any thermostats."""
    ecomax.handle_frame(Response(data={ATTR_THERMOSTAT_COUNT: 0}))
    ecomax.handle_frame(
        ThermostatParametersResponse(
            message=messages[FrameType.RESPONSE_THERMOSTAT_PARAMETERS]
        )
    )
    await ecomax.wait_until_done()
    assert not await ecomax.get(ATTR_THERMOSTAT_PARAMETERS)
    thermostat_profile = await ecomax.get(ATTR_THERMOSTAT_PROFILE)
    assert thermostat_profile is None


async def test_thermostat_profile_callbacks(
    ecomax: EcoMAX, messages: dict[FrameType, bytearray]
) -> None:
    """Test callbacks that are dispatchd on receiving thermostat profile."""
    ecomax.handle_frame(Response(data={ATTR_THERMOSTAT_COUNT: 3}))
    ecomax.handle_frame(
        ThermostatParametersResponse(
            message=messages[FrameType.RESPONSE_THERMOSTAT_PARAMETERS]
        )
    )
    await ecomax.wait_until_done()
    thermostat_profile = await ecomax.get(ATTR_THERMOSTAT_PROFILE)
    assert thermostat_profile.value == 0.0
    assert thermostat_profile.min_value == 0.0
    assert thermostat_profile.max_value == 5.0
    assert isinstance(thermostat_profile.request, SetThermostatParameterRequest)
    assert thermostat_profile.request.data == {
        ATTR_INDEX: 0,
        ATTR_VALUE: 0,
        ATTR_OFFSET: 0,
        ATTR_SIZE: 1,
    }

    # Test when thermostat profile is none.
    ecomax.handle_frame(Response(data={ATTR_THERMOSTAT_PROFILE: None}))
    await ecomax.wait_until_done()
    assert await ecomax.get(ATTR_THERMOSTAT_PROFILE) is None


async def test_mixer_parameters_callbacks(
    ecomax: EcoMAX, messages: dict[FrameType, bytearray]
) -> None:
    """Test callbacks that are dispatchd on receiving mixer parameters."""
    ecomax.handle_frame(
        MixerParametersResponse(message=messages[FrameType.RESPONSE_MIXER_PARAMETERS])
    )
    await ecomax.wait_until_done()
    mixers = await ecomax.get(ATTR_MIXERS)
    assert len(mixers) == 1
    mixer = mixers[0]
    assert len(mixer.data) == 6
    mixer_target_temp = await mixer.get("mixer_target_temp")
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

    weather_control = await mixer.get("weather_control")
    assert isinstance(weather_control, MixerBinaryParameter)
    assert weather_control.value == STATE_ON

    heat_curve = await mixer.get("heat_curve")
    assert isinstance(heat_curve, MixerParameter)
    assert heat_curve.value == 1.3
    assert heat_curve.min_value == 1.0
    assert heat_curve.max_value == 3.0


async def test_mixer_parameters_callbacks_without_mixers(ecomax: EcoMAX) -> None:
    """Test mixer parameters callbacks without any mixers."""
    ecomax.handle_frame(MixerParametersResponse(data={ATTR_MIXER_PARAMETERS: None}))
    await ecomax.wait_until_done()
    assert not await ecomax.get(ATTR_MIXER_PARAMETERS)


async def test_schedule_callback(
    ecomax: EcoMAX,
    messages: dict[FrameType, bytearray],
    data: dict[FrameType, EventDataType],
) -> None:
    """Test callback that is dispatchd on receiving schedule data."""
    ecomax.handle_frame(
        SchedulesResponse(message=messages[FrameType.RESPONSE_SCHEDULES])
    )
    schedules = await ecomax.get(ATTR_SCHEDULES)
    assert len(schedules) == 1
    heating_schedule = schedules["heating"]
    assert isinstance(heating_schedule, Schedule)

    heating_schedule_switch = await ecomax.get("heating_schedule_switch")
    assert heating_schedule_switch.value == STATE_OFF
    assert isinstance(heating_schedule_switch, ScheduleBinaryParameter)

    heating_schedule_parameter = await ecomax.get("heating_schedule_parameter")
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


async def test_request(ecomax: EcoMAX) -> None:
    """Test requesting the value."""

    with patch(
        "pyplumio.devices.ecomax.EcoMAX.get",
        side_effect=(asyncio.TimeoutError, True),
    ) as mock_get, patch("asyncio.Queue.put_nowait") as mock_put_nowait:
        assert await ecomax.request("foo", FrameType.REQUEST_ALERTS, timeout=5)

    mock_get.assert_awaited_with("foo", timeout=5)
    assert mock_put_nowait.call_count == 2
    args, _ = mock_put_nowait.call_args
    assert isinstance(args[0], AlertsRequest)


async def test_request_error(ecomax: EcoMAX) -> None:
    """Test requesting the value with error."""
    with patch(
        "pyplumio.devices.ecomax.EcoMAX.get",
        side_effect=(asyncio.TimeoutError, asyncio.TimeoutError),
    ), pytest.raises(ValueError):
        await ecomax.request("foo", FrameType.REQUEST_ALERTS, retries=1)


@patch("pyplumio.helpers.parameter.Parameter.is_changed", False)
async def test_set(ecomax: EcoMAX, messages: dict[FrameType, bytearray]) -> None:
    """Test setting parameter value via set helper."""
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

    # Test setting an ecomax parameter.
    assert await ecomax.set("fuel_flow_kg_h", 13.0)
    fuel_flow_kg_h = await ecomax.get("fuel_flow_kg_h")
    assert fuel_flow_kg_h.value == 13.0

    # Test setting an ecomax parameter without blocking.
    with patch("pyplumio.devices.Device.set", new_callable=Mock), patch(
        "pyplumio.helpers.task_manager.TaskManager.create_task"
    ) as mock_create_task:
        ecomax.set_nowait("fuel_flow_kg_h", 10)

    mock_create_task.assert_called_once()

    # Test setting a thermostat parameter.
    thermostat = ecomax.data[ATTR_THERMOSTATS][0]
    assert await thermostat.set("party_target_temp", 21.0)
    target_party_temp = await thermostat.get("party_target_temp")
    assert target_party_temp.value == 21.0

    # Test setting a mixer parameter.
    mixer = ecomax.data[ATTR_MIXERS][0]
    assert await mixer.set("mixer_target_temp", 35.0)
    mixer_target_temp = await mixer.get("mixer_target_temp")
    assert mixer_target_temp.value == 35.0

    # Test with invalid parameter.
    ecomax.data["bar"] = Mock()
    with pytest.raises(ParameterNotFoundError):
        await ecomax.set("bar", 1)


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


async def test_shutdown(ecomax: EcoMAX, messages: dict[FrameType, bytearray]) -> None:
    """Test device tasks shutdown."""
    ecomax.handle_frame(
        SensorDataMessage(message=messages[FrameType.MESSAGE_SENSOR_DATA])
    )
    await ecomax.wait_until_done()

    with patch("pyplumio.devices.Mixer.shutdown") as mock_mixer_shutdown, patch(
        "pyplumio.devices.Thermostat.shutdown"
    ) as mock_thermostat_shutdown, patch(
        "pyplumio.devices.Device.cancel_tasks"
    ) as mock_cancel_tasks, patch(
        "pyplumio.devices.Device.wait_until_done"
    ) as mock_wait_until_done:
        await ecomax.shutdown()

    mock_wait_until_done.assert_awaited_once()
    mock_cancel_tasks.assert_called_once()
    mock_thermostat_shutdown.assert_awaited_once()
    mock_mixer_shutdown.assert_awaited_once()
