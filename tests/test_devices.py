"""Contains tests for the device handler classes."""

import asyncio
from unittest.mock import AsyncMock, Mock, call, patch

import pytest

from pyplumio.const import (
    ATTR_DEVICE_INDEX,
    ATTR_FRAME_ERRORS,
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
    UnitOfMeasurement,
)
from pyplumio.devices import get_device_handler
from pyplumio.devices.ecomax import (
    ATTR_FUEL_BURNED,
    ATTR_MIXERS,
    ATTR_THERMOSTATS,
    SETUP_FRAME_TYPES,
    EcoMAX,
)
from pyplumio.devices.ecoster import EcoSTER
from pyplumio.devices.mixer import Mixer
from pyplumio.devices.thermostat import Thermostat
from pyplumio.exceptions import ParameterNotFoundError, UnknownDeviceError
from pyplumio.frames import Response
from pyplumio.frames.messages import RegulatorDataMessage, SensorDataMessage
from pyplumio.frames.requests import (
    AlertsRequest,
    EcomaxControlRequest,
    RegulatorDataSchemaRequest,
    SchedulesRequest,
    SetEcomaxParameterRequest,
    SetMixerParameterRequest,
    SetScheduleRequest,
    SetThermostatParameterRequest,
    UIDRequest,
)
from pyplumio.frames.responses import (
    EcomaxParametersResponse,
    MixerParametersResponse,
    RegulatorDataSchemaResponse,
    SchedulesResponse,
    ThermostatParametersResponse,
)
from pyplumio.helpers.schedule import Schedule
from pyplumio.structures.ecomax_parameters import (
    ATTR_ECOMAX_CONTROL,
    EcomaxBinaryParameter,
    EcomaxParameter,
)
from pyplumio.structures.frame_versions import ATTR_FRAME_VERSIONS
from pyplumio.structures.fuel_consumption import ATTR_FUEL_CONSUMPTION
from pyplumio.structures.mixer_parameters import (
    ATTR_MIXER_PARAMETERS,
    MixerBinaryParameter,
    MixerParameter,
)
from pyplumio.structures.mixer_sensors import ATTR_MIXER_SENSORS
from pyplumio.structures.network_info import NetworkInfo
from pyplumio.structures.regulator_data import ATTR_REGDATA, RegulatorData
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
from pyplumio.structures.thermostat_sensors import (
    ATTR_THERMOSTAT_SENSORS,
    ATTR_THERMOSTATS_AVAILABLE,
    ATTR_THERMOSTATS_CONNECTED,
)
from tests import load_json_parameters, load_json_test_data

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


async def test_int(ecoster: EcoSTER) -> None:
    """Test getting addressable device's address via int()."""
    assert int(ecoster) == DeviceType.ECOSTER


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
    assert not ecomax.data[ATTR_FRAME_ERRORS]
    assert mock_request.await_count == len(SETUP_FRAME_TYPES)


async def test_async_setup_error() -> None:
    """Test with error during requesting initial data frames."""
    ecomax = EcoMAX(asyncio.Queue(), network=NetworkInfo())

    with patch("pyplumio.devices.ecomax.EcoMAX.wait_for"), patch(
        "pyplumio.devices.ecomax.EcoMAX.request",
        side_effect=(
            ValueError("test", FrameType.REQUEST_ALERTS),
            True,
            True,
            True,
            True,
            True,
            True,
            True,
        ),
    ) as mock_request:
        await ecomax.async_setup()
        await ecomax.wait_until_done()

    assert await ecomax.get(ATTR_LOADED)
    assert ecomax.data[ATTR_FRAME_ERRORS][0] == FrameType.REQUEST_ALERTS
    assert mock_request.await_count == len(SETUP_FRAME_TYPES)


async def test_frame_versions_update(ecomax: EcoMAX) -> None:
    """Test requesting updated frames."""
    test_data = load_json_test_data("messages/sensor_data.json")[0]
    with patch("asyncio.Queue.put_nowait") as mock_put_nowait:
        ecomax.handle_frame(SensorDataMessage(message=test_data["message"]))
        await ecomax.wait_until_done()

    mock_put_nowait.assert_has_calls(
        [
            call(RegulatorDataSchemaRequest(recipient=DeviceType.ECOMAX)),
            call(SchedulesRequest(recipient=DeviceType.ECOMAX)),
            call(UIDRequest(recipient=DeviceType.ECOMAX)),
            call(AlertsRequest(recipient=DeviceType.ECOMAX)),
        ]
    )


async def test_ecomax_data_callbacks(ecomax: EcoMAX) -> None:
    """Test callbacks that are dispatched on received data frames."""
    test_data = load_json_test_data("messages/sensor_data.json")[0]
    ecomax.handle_frame(SensorDataMessage(message=test_data["message"]))
    await ecomax.wait_until_done()
    heating_target = await ecomax.get("heating_target")
    assert heating_target == 41.0

    ecomax_control = await ecomax.get(ATTR_ECOMAX_CONTROL)
    assert isinstance(ecomax_control, EcomaxBinaryParameter)
    assert isinstance(ecomax_control.request, EcomaxControlRequest)
    assert ecomax_control.value == STATE_OFF
    assert ecomax_control.request.data == {ATTR_VALUE: 0}


async def test_ecomax_parameters_callbacks(ecomax: EcoMAX) -> None:
    """Test callbacks that are dispatched on received parameter frames."""
    test_data = load_json_test_data("responses/ecomax_parameters.json")[0]
    ecomax.handle_frame(EcomaxParametersResponse(message=test_data["message"]))
    await ecomax.wait_until_done()
    fuzzy_logic = await ecomax.get("fuzzy_logic")
    assert isinstance(fuzzy_logic, EcomaxBinaryParameter)
    assert isinstance(fuzzy_logic.request, SetEcomaxParameterRequest)
    assert fuzzy_logic == STATE_ON
    assert fuzzy_logic.value == STATE_ON
    assert fuzzy_logic.request.data == {
        ATTR_INDEX: 18,
        ATTR_VALUE: 1,
    }

    # Test that parameter instance is not recreated on subsequent calls.
    ecomax.handle_frame(EcomaxParametersResponse(message=test_data["message"]))
    await ecomax.wait_until_done()
    assert await ecomax.get("fuzzy_logic") is fuzzy_logic

    # Test parameter with the multiplier (heating_heat_curve)
    heating_heat_curve = await ecomax.get("heating_curve")
    assert heating_heat_curve.value == 1.3
    assert heating_heat_curve.min_value == 0.1
    assert heating_heat_curve.max_value == 4.0

    # Test setting parameter with the multiplier.
    with patch(
        "pyplumio.structures.ecomax_parameters.Parameter.set", new_callable=AsyncMock
    ) as mock_set:
        await heating_heat_curve.set(2.5)

    mock_set.assert_awaited_once_with(25, 5)

    # Test parameter with the offset (heating_heat_curve_shift)
    heating_heat_curve_shift: EcomaxParameter = await ecomax.get("heating_curve_shift")
    assert heating_heat_curve_shift.value == 0.0
    assert heating_heat_curve_shift.min_value == -20.0
    assert heating_heat_curve_shift.max_value == 20.0
    assert heating_heat_curve_shift.unit_of_measurement == UnitOfMeasurement.CELSIUS

    # Test setting the parameter with the offset.
    with patch(
        "pyplumio.structures.ecomax_parameters.Parameter.set", new_callable=AsyncMock
    ) as mock_set:
        await heating_heat_curve_shift.set(1)

    mock_set.assert_awaited_once_with(21, 5)


async def test_unknown_ecomax_parameter(ecomax: EcoMAX, caplog) -> None:
    """Test unknown ecoMAX parameter."""
    test_data = load_json_test_data("unknown/unknown_ecomax_parameter.json")
    ecomax.handle_frame(EcomaxParametersResponse(message=test_data["message"]))
    await ecomax.wait_until_done()
    assert "unknown ecoMAX parameter (139)" in caplog.text
    assert "ParameterValues(value=1, min_value=1, max_value=1)" in caplog.text
    assert "ecoMAX 350P2-ZF" in caplog.text


@patch(
    "time.perf_counter_ns",
    side_effect=(0, 10 * 1000000000, 600 * 1000000000, 610 * 1000000000),
)
async def test_fuel_consumption_callbacks(mock_time, caplog) -> None:
    """Test callbacks that are dispatched on received fuel consumption."""
    ecomax = EcoMAX(asyncio.Queue(), network=NetworkInfo())
    ecomax.handle_frame(Response(data={ATTR_FUEL_CONSUMPTION: 3.6}))
    await ecomax.wait_until_done()
    fuel_burned = await ecomax.get(ATTR_FUEL_BURNED)
    assert fuel_burned == 0.01
    ecomax.handle_frame(Response(data={ATTR_FUEL_CONSUMPTION: 1}))
    await ecomax.wait_until_done()
    assert "Skipping outdated fuel consumption" in caplog.text


async def test_regdata_callbacks(ecomax: EcoMAX) -> None:
    """Test callbacks that are dispatched on received regdata."""
    test_schema, test_regdata = (
        load_json_test_data("responses/regulator_data_schema.json")[0],
        load_json_test_data("messages/regulator_data.json")[0],
    )
    ecomax.handle_frame(RegulatorDataSchemaResponse(message=test_schema["message"]))
    await ecomax.wait_until_done()
    ecomax.handle_frame(RegulatorDataMessage(message=test_regdata["message"]))
    await ecomax.wait_until_done()
    regdata = await ecomax.get(ATTR_REGDATA)
    assert isinstance(regdata, RegulatorData)


async def test_regdata_callbacks_without_schema(ecomax: EcoMAX) -> None:
    """Test callbacks that are dispatched on received regdata."""
    test_data = load_json_test_data("messages/regulator_data.json")[0]
    ecomax.handle_frame(RegulatorDataMessage(message=test_data["message"]))
    await ecomax.wait_until_done()
    assert ATTR_FRAME_VERSIONS in ecomax.data
    assert ATTR_REGDATA not in ecomax.data


async def test_mixer_sensors_callbacks(ecomax: EcoMAX) -> None:
    """Test callbacks that are dispatched on receiving mixer sensors info."""
    ecomax.handle_frame(
        SensorDataMessage(
            message=load_json_test_data("messages/sensor_data.json")[0]["message"]
        )
    )
    await ecomax.wait_until_done()
    mixers = await ecomax.get(ATTR_MIXERS)
    assert len(mixers) == 1
    mixer = mixers[4]
    assert isinstance(mixer, Mixer)
    assert mixer.index == 4
    assert mixer.data == {
        "current_temp": 20.0,
        "target_temp": 40,
        "pump": False,
        "mixer_sensors": True,
    }


async def test_mixer_sensors_callbacks_without_mixers(ecomax: EcoMAX) -> None:
    """Test callbacks that are dispatched on receiving mixer sensors
    without any mixers."""
    ecomax.handle_frame(MixerParametersResponse(data={ATTR_MIXER_SENSORS: {}}))
    await ecomax.wait_until_done()
    assert not await ecomax.get(ATTR_MIXER_SENSORS)


async def test_thermostat_sensors_callbacks(ecomax: EcoMAX) -> None:
    """Test callbacks that are dispatched on receiving thermostat sensors info."""
    test_data = load_json_test_data("messages/sensor_data.json")[0]
    ecomax.handle_frame(SensorDataMessage(message=test_data["message"]))
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
        "thermostat_sensors": True,
    }
    assert await ecomax.get(ATTR_THERMOSTATS_AVAILABLE) == 2
    assert await ecomax.get(ATTR_THERMOSTATS_CONNECTED) == 1


async def test_thermostat_sensors_callbacks_without_thermostats(ecomax: EcoMAX) -> None:
    """Test callbacks that are dispatched on receiving thermostats sensors
    without any thermostats."""
    ecomax.handle_frame(
        ThermostatParametersResponse(data={ATTR_THERMOSTAT_SENSORS: {}})
    )
    await ecomax.wait_until_done()
    assert not await ecomax.get(ATTR_THERMOSTAT_SENSORS)


async def test_thermostat_parameters_callbacks(ecomax: EcoMAX) -> None:
    """Test callbacks that are dispatched on receiving thermostat parameters."""
    test_data = load_json_test_data("responses/thermostat_parameters.json")[0]
    ecomax.handle_frame(Response(data={ATTR_THERMOSTATS_CONNECTED: 3}))
    await ecomax.wait_until_done()
    ecomax.handle_frame(ThermostatParametersResponse(message=test_data["message"]))
    await ecomax.wait_until_done()
    thermostats = await ecomax.get(ATTR_THERMOSTATS)
    assert len(thermostats) == 1
    thermostat = thermostats[0]
    assert len(thermostat.data) == 13
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

    # Test that parameter instance is not recreated on subsequent calls.
    ecomax.handle_frame(ThermostatParametersResponse(message=test_data["message"]))
    await ecomax.wait_until_done()
    thermostats = await ecomax.get(ATTR_THERMOSTATS)
    thermostat = thermostats[0]
    assert await thermostat.get("party_target_temp") is party_target_temp


async def test_thermostat_parameters_callbacks_without_thermostats(
    ecomax: EcoMAX,
) -> None:
    """Test callbacks that are dispatched on receiving thermostat parameters
    without any thermostats."""
    test_data = load_json_test_data("responses/thermostat_parameters.json")[0]
    ecomax.handle_frame(Response(data={ATTR_THERMOSTATS_CONNECTED: 0}))
    ecomax.handle_frame(ThermostatParametersResponse(message=test_data["message"]))
    await ecomax.wait_until_done()
    assert not await ecomax.get(ATTR_THERMOSTAT_PARAMETERS)


async def test_thermostat_profile_callbacks(ecomax: EcoMAX) -> None:
    """Test callbacks that are dispatched on receiving thermostat profile."""
    ecomax.handle_frame(Response(data={ATTR_THERMOSTATS_CONNECTED: 3}))
    await ecomax.wait_until_done()
    ecomax.handle_frame(
        ThermostatParametersResponse(
            message=load_json_test_data("responses/thermostat_parameters.json")[0][
                "message"
            ]
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


async def test_mixer_parameters_callbacks(ecomax: EcoMAX) -> None:
    """Test callbacks that are dispatched on receiving mixer parameters."""
    test_data = load_json_test_data("responses/mixer_parameters.json")[0]
    ecomax.handle_frame(MixerParametersResponse(message=test_data["message"]))
    await ecomax.wait_until_done()
    mixers = await ecomax.get(ATTR_MIXERS)
    assert len(mixers) == 1
    mixer = mixers[0]
    assert len(mixer.data) == 7
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

    heat_curve = await mixer.get("heating_curve")
    assert isinstance(heat_curve, MixerParameter)
    assert heat_curve.value == 1.3
    assert heat_curve.min_value == 1.0
    assert heat_curve.max_value == 3.0

    # Test that parameter instance is not recreated on subsequent calls.
    ecomax.handle_frame(MixerParametersResponse(message=test_data["message"]))
    await ecomax.wait_until_done()
    mixers = await ecomax.get(ATTR_MIXERS)
    mixer = mixers[0]
    assert await mixer.get("mixer_target_temp") is mixer_target_temp


async def test_mixer_parameters_callbacks_without_mixers(ecomax: EcoMAX) -> None:
    """Test mixer parameters callbacks without any mixers."""
    ecomax.handle_frame(MixerParametersResponse(data={ATTR_MIXER_PARAMETERS: {}}))
    await ecomax.wait_until_done()
    assert not await ecomax.get(ATTR_MIXER_PARAMETERS)


async def test_unknown_mixer_parameter(ecomax: EcoMAX, caplog) -> None:
    """Test unknown mixer parameter."""
    test_data = load_json_test_data("unknown/unknown_mixer_parameter.json")
    ecomax.handle_frame(MixerParametersResponse(message=test_data["message"]))
    await ecomax.wait_until_done()
    assert "unknown mixer parameter (14)" in caplog.text
    assert "ParameterValues(value=1, min_value=1, max_value=1)" in caplog.text
    assert "ecoMAX 350P2-ZF" in caplog.text


@pytest.mark.parametrize(
    "message, data",
    load_json_parameters("responses/schedules.json"),
)
async def test_schedule_callback(ecomax: EcoMAX, message, data) -> None:
    """Test callback that is dispatched on receiving schedule data."""
    ecomax.handle_frame(SchedulesResponse(message=message))
    await ecomax.wait_until_done()
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

    schedule_data = data[ATTR_SCHEDULES][0][1]
    for index, weekday in enumerate(
        ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
    ):
        schedule = getattr(heating_schedule, weekday)
        assert schedule.intervals == schedule_data[index]

    # Test that parameter instance is not recreated on subsequent calls.
    ecomax.handle_frame(SchedulesResponse(message=message))
    await ecomax.wait_until_done()
    assert await ecomax.get("heating_schedule_switch") is heating_schedule_switch


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


@patch("pyplumio.helpers.parameter.Parameter.pending_update", False)
async def test_set(ecomax: EcoMAX) -> None:
    """Test setting parameter value via set helper."""
    test_ecomax_data, test_thermostat_data, test_mixer_data = (
        load_json_test_data("responses/ecomax_parameters.json")[0],
        load_json_test_data("responses/thermostat_parameters.json")[0],
        load_json_test_data("responses/mixer_parameters.json")[0],
    )
    ecomax.handle_frame(Response(data={ATTR_THERMOSTATS_CONNECTED: 3}))
    await ecomax.wait_until_done()
    ecomax.handle_frame(EcomaxParametersResponse(message=test_ecomax_data["message"]))
    ecomax.handle_frame(
        ThermostatParametersResponse(message=test_thermostat_data["message"])
    )
    ecomax.handle_frame(MixerParametersResponse(message=test_mixer_data["message"]))

    # Test setting an ecomax parameter.
    assert await ecomax.set("max_fuel_flow", 13.0)
    max_fuel_flow = await ecomax.get("max_fuel_flow")
    assert max_fuel_flow.value == 13.0

    # Test setting an ecomax parameter without blocking.
    with patch("pyplumio.devices.Device.set", new_callable=Mock), patch(
        "pyplumio.helpers.task_manager.TaskManager.create_task"
    ) as mock_create_task:
        ecomax.set_nowait("max_fuel_flow", 10)

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


async def test_turn_on(ecomax: EcoMAX, caplog) -> None:
    """Test turning the controller on."""
    assert not await ecomax.turn_on()
    assert "ecoMAX control isn't available" in caplog.text
    ecomax.data[ATTR_ECOMAX_CONTROL] = AsyncMock()
    assert await ecomax.turn_on()
    ecomax.data[ATTR_ECOMAX_CONTROL].turn_on.assert_awaited_once()


async def test_turn_off(ecomax: EcoMAX, caplog) -> None:
    """Test turning the controller off."""
    await ecomax.turn_off()
    assert "ecoMAX control isn't available" in caplog.text
    ecomax.data[ATTR_ECOMAX_CONTROL] = AsyncMock()
    await ecomax.turn_off()
    ecomax.data[ATTR_ECOMAX_CONTROL].turn_off.assert_awaited_once()


@patch("pyplumio.devices.ecomax.EcoMAX.create_task")
@patch("pyplumio.devices.ecomax.EcoMAX.turn_on", new_callable=Mock)
async def test_turn_on_nowait(mock_create_task, mock_turn_on, ecomax: EcoMAX) -> None:
    """Test turning the controller on without waiting."""
    ecomax.turn_on_nowait()
    await ecomax.wait_until_done()
    mock_create_task.assert_called_once()
    mock_turn_on.assert_called_once()


@patch("pyplumio.devices.ecomax.EcoMAX.create_task")
@patch("pyplumio.devices.ecomax.EcoMAX.turn_off", new_callable=Mock)
async def test_turn_off_nowait(mock_create_task, mock_turn_off, ecomax: EcoMAX) -> None:
    """Test turning the controller on without waiting."""
    ecomax.turn_off_nowait()
    await ecomax.wait_until_done()
    mock_create_task.assert_called_once()
    mock_turn_off.assert_called_once()


async def test_shutdown(ecomax: EcoMAX) -> None:
    """Test device tasks shutdown."""
    ecomax.handle_frame(
        SensorDataMessage(
            message=load_json_test_data("messages/sensor_data.json")[0]["message"]
        )
    )
    await ecomax.wait_until_done()

    with patch("pyplumio.devices.mixer.Mixer.shutdown") as mock_mixer_shutdown, patch(
        "pyplumio.devices.thermostat.Thermostat.shutdown"
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
