"""Contains tests for devices."""

import asyncio
from typing import Dict, Tuple
from unittest.mock import AsyncMock, Mock, call, patch
import warnings

import pytest

from pyplumio.const import (
    ATTR_ECOMAX_PARAMETERS,
    ATTR_ECOMAX_SENSORS,
    ATTR_FRAME_VERSIONS,
    ATTR_FUEL_BURNED,
    ATTR_FUEL_CONSUMPTION,
    ATTR_MIXER_PARAMETERS,
    ATTR_MIXER_SENSORS,
    ATTR_MIXERS,
    ATTR_REGDATA,
    ATTR_SCHEDULE,
    ATTR_SCHEDULES,
    ATTR_STATE,
    ATTR_THERMOSTAT_SENSORS,
    ATTR_THERMOSTATS,
    ATTR_THERMOSTATS_NUMBER,
    DeviceType,
    FrameType,
)
from pyplumio.devices import Mixer, Thermostat, get_device_handler
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.devices.ecoster import EcoSTER
from pyplumio.exceptions import ParameterNotFoundError, UnknownDeviceError
from pyplumio.frames import Response
from pyplumio.frames.messages import RegulatorDataMessage
from pyplumio.frames.requests import (
    AlertsRequest,
    DataSchemaRequest,
    EcomaxParametersRequest,
    MixerParametersRequest,
    PasswordRequest,
    SchedulesRequest,
    StartMasterRequest,
    ThermostatParametersRequest,
    UIDRequest,
)
from pyplumio.frames.responses import DataSchemaResponse, ThermostatParametersResponse
from pyplumio.helpers.frame_versions import DEFAULT_FRAME_VERSION, FrameVersions
from pyplumio.helpers.parameter import (
    EcomaxBinaryParameter,
    MixerBinaryParameter,
    MixerParameter,
    Parameter,
    ScheduleBinaryParameter,
    ScheduleParameter,
    ThermostatParameter,
)
from pyplumio.helpers.schedule import Schedule
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.structures.ecomax_parameters import ATTR_ECOMAX_CONTROL
from pyplumio.structures.statuses import ATTR_HEATING_TARGET
from pyplumio.structures.temperatures import ATTR_HEATING_TEMP
from pyplumio.structures.thermostat_parameters import ATTR_THERMOSTAT_PROFILE

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


async def test_frame_versions_update(ecomax: EcoMAX) -> None:
    """Test requesting updated frames."""
    versions = FrameVersions(ecomax)
    with patch("asyncio.Queue.put_nowait") as mock_put_nowait:
        await versions.async_update(
            {
                FrameType.REQUEST_START_MASTER: DEFAULT_FRAME_VERSION,
                UNKNOWN_FRAME: DEFAULT_FRAME_VERSION,
            }
        )
        await versions.async_update(
            {int(x): DEFAULT_FRAME_VERSION for x in ecomax.required_frames}
        )

    calls = [
        call(StartMasterRequest(recipient=DeviceType.ECOMAX)),
        call(UIDRequest(recipient=DeviceType.ECOMAX)),
        call(DataSchemaRequest(recipient=DeviceType.ECOMAX)),
        call(EcomaxParametersRequest(recipient=DeviceType.ECOMAX)),
        call(MixerParametersRequest(recipient=DeviceType.ECOMAX)),
        call(PasswordRequest(recipient=DeviceType.ECOMAX)),
        call(AlertsRequest(recipient=DeviceType.ECOMAX)),
        call(SchedulesRequest(recipient=DeviceType.ECOMAX)),
        call(ThermostatParametersRequest(recipient=DeviceType.ECOMAX)),
    ]
    mock_put_nowait.assert_has_calls(calls)
    assert versions.versions == {
        FrameType.REQUEST_START_MASTER: DEFAULT_FRAME_VERSION,
        FrameType.REQUEST_UID: DEFAULT_FRAME_VERSION,
        FrameType.REQUEST_DATA_SCHEMA: DEFAULT_FRAME_VERSION,
        FrameType.REQUEST_ECOMAX_PARAMETERS: DEFAULT_FRAME_VERSION,
        FrameType.REQUEST_MIXER_PARAMETERS: DEFAULT_FRAME_VERSION,
        FrameType.REQUEST_PASSWORD: DEFAULT_FRAME_VERSION,
        FrameType.REQUEST_ALERTS: DEFAULT_FRAME_VERSION,
        FrameType.REQUEST_SCHEDULES: DEFAULT_FRAME_VERSION,
        FrameType.REQUEST_THERMOSTAT_PARAMETERS: DEFAULT_FRAME_VERSION,
    }


async def test_ecomax_data_callbacks(ecomax: EcoMAX) -> None:
    """Test callbacks that are fired on received data frames."""
    frames = (
        Response(data={ATTR_ECOMAX_SENSORS: {"test_sensor": 42}}),
        Response(data={ATTR_STATE: 1}),
    )
    for frame in frames:
        ecomax.handle_frame(frame)

    assert await ecomax.get_value("test_sensor") == 42
    ecomax_control = await ecomax.get_parameter("ecomax_control")
    assert isinstance(ecomax_control, EcomaxBinaryParameter)
    assert ecomax_control.value == 1


async def test_ecomax_parameters_callbacks(ecomax: EcoMAX) -> None:
    """Test callbacks that are fired on received parameter frames."""
    ecomax.handle_frame(
        Response(
            data={
                ATTR_ECOMAX_PARAMETERS: [
                    (0, [0, 0, 1]),
                    (1, [10, 5, 20]),
                ]
            }
        )
    )

    assert await ecomax.get_value("airflow_power_100") == 0
    test_binary_parameter = await ecomax.get_parameter("airflow_power_100")
    assert isinstance(test_binary_parameter, EcomaxBinaryParameter)
    assert await ecomax.get_value("airflow_power_50") == 10
    test_parameter = await ecomax.get_parameter("airflow_power_50")
    assert test_parameter.value == 10
    assert test_parameter.min_value == 5
    assert test_parameter.max_value == 20


@patch("time.time", side_effect=(0, 10, 600, 610))
async def test_fuel_consumption_callbacks(mock_time, caplog) -> None:
    """Test callbacks that are fired on received fuel consumption."""
    ecomax = EcoMAX(asyncio.Queue())
    ecomax.handle_frame(Response(data={ATTR_FUEL_CONSUMPTION: 3.6}))
    ecomax.handle_frame(Response(data={ATTR_FUEL_CONSUMPTION: 1}))
    await ecomax.wait_until_done()
    assert await ecomax.get_value(ATTR_FUEL_BURNED) == 0.01
    assert "Skipping outdated fuel consumption" in caplog.text


async def test_regdata_callbacks(
    ecomax: EcoMAX, messages: Dict[int, bytearray]
) -> None:
    """Test callbacks that are fired on received regdata."""
    # Test handling regdata without data schema.
    ecomax.handle_frame(
        RegulatorDataMessage(message=messages[FrameType.MESSAGE_REGULATOR_DATA])
    )
    await ecomax.wait_until_done()
    assert await ecomax.get_value(ATTR_FRAME_VERSIONS)

    # Set data schema and decode the regdata.
    ecomax.handle_frame(
        DataSchemaResponse(message=messages[FrameType.RESPONSE_DATA_SCHEMA])
    )
    ecomax.handle_frame(
        RegulatorDataMessage(message=messages[FrameType.MESSAGE_REGULATOR_DATA])
    )
    await ecomax.wait_until_done()

    regdata = await ecomax.get_value(ATTR_REGDATA)
    assert regdata[ATTR_STATE] == 0
    assert round(regdata[ATTR_HEATING_TEMP], 1) == 22.4
    assert regdata[ATTR_HEATING_TARGET] == 41
    assert regdata["183"] == "0.0.0.0"
    assert regdata["184"] == "255.255.255.0"


async def test_mixer_sensors_callbacks(ecomax: EcoMAX) -> None:
    """Test callbacks that are fired on receiving mixer sensors info."""
    ecomax.handle_frame(Response(data={ATTR_MIXER_SENSORS: [(0, {"test_sensor": 42})]}))
    mixers = await ecomax.get_value(ATTR_MIXERS)
    assert len(mixers) == 1
    assert isinstance(mixers[0], Mixer)
    assert mixers[0].mixer_number == 0
    assert await mixers[0].get_value("test_sensor") == 42


async def test_thermostat_sensors_callbacks(ecomax: EcoMAX) -> None:
    """Test callbacks that are fired on receiving thermostat sensors info."""
    ecomax.handle_frame(
        Response(data={ATTR_THERMOSTAT_SENSORS: [(0, {"test_sensor": 42})]})
    )
    await ecomax.wait_until_done()
    thermostats = await ecomax.get_value(ATTR_THERMOSTATS)
    assert len(thermostats) == 1
    assert isinstance(thermostats[0], Thermostat)
    assert thermostats[0].thermostat_number == 0
    assert await thermostats[0].get_value("test_sensor") == 42


async def test_thermostat_parameters_callbacks(
    ecomax: EcoMAX, messages: Dict[int, bytearray]
) -> None:
    """Test callbacks that are fired on receiving thermostat parameters."""
    # Test handling thermostat parameters without thermostats.
    ecomax.handle_frame(Response(data={ATTR_THERMOSTAT_SENSORS: []}))
    ecomax.handle_frame(
        ThermostatParametersResponse(
            message=messages[FrameType.RESPONSE_THERMOSTAT_PARAMETERS]
        )
    )
    await ecomax.wait_until_done()
    assert ATTR_THERMOSTAT_PROFILE not in ecomax.data
    assert ATTR_THERMOSTATS not in ecomax.data

    # Test handling thermostat parameters with two thermostats.
    ecomax.handle_frame(Response(data={ATTR_THERMOSTATS_NUMBER: 2}))
    ecomax.handle_frame(
        ThermostatParametersResponse(
            message=messages[FrameType.RESPONSE_THERMOSTAT_PARAMETERS]
        )
    )
    await ecomax.wait_until_done()
    thermostats = await ecomax.get_value(ATTR_THERMOSTATS)
    assert len(thermostats) == 2
    assert await thermostats[0].get_parameter("thermostat_mode")
    assert await ecomax.get_parameter(ATTR_THERMOSTAT_PROFILE)


async def test_thermostat_profile_callbacks(ecomax: EcoMAX) -> None:
    """Test callbacks that are fired on receiving thermostat profile."""
    test_parameter = ThermostatParameter(
        device=ecomax, name=ATTR_THERMOSTAT_PROFILE, value=2, min_value=0, max_value=5
    )
    ecomax.handle_frame(Response(data={ATTR_THERMOSTAT_PROFILE: (2, 0, 5)}))
    await ecomax.wait_until_done()
    assert await ecomax.get_parameter(ATTR_THERMOSTAT_PROFILE) == test_parameter

    # Test when parameter is None.
    ecomax.handle_frame(Response(data={ATTR_THERMOSTAT_PROFILE: None}))
    await ecomax.wait_until_done()
    assert await ecomax.get_value(ATTR_THERMOSTAT_PROFILE) is None


async def test_mixer_parameters_callbacks(ecomax: EcoMAX) -> None:
    """Test callbacks that are fired on receiving mixer parameters."""
    ecomax.handle_frame(
        Response(
            data={
                ATTR_MIXER_PARAMETERS: [
                    (
                        0,
                        [
                            (0, [0, 0, 1]),
                            (1, [10, 5, 20]),
                        ],
                    )
                ]
            }
        )
    )
    mixers = await ecomax.get_value(ATTR_MIXERS)
    test_binary_parameter = await mixers[0].get_parameter("mixer_target_temp")
    assert test_binary_parameter.value == 0
    assert isinstance(test_binary_parameter, MixerBinaryParameter)
    test_parameter = await mixers[0].get_parameter("min_mixer_target_temp")
    assert isinstance(test_parameter, MixerParameter)
    assert test_parameter.value == 10
    assert test_parameter.min_value == 5
    assert test_parameter.max_value == 20


async def test_schedule_callback(
    ecomax: EcoMAX, data: Dict[int, DeviceDataType]
) -> None:
    """Test callback that is fired on receiving schedule data."""
    ecomax.handle_frame(Response(data=data[FrameType.RESPONSE_SCHEDULES]))
    schedule = (await ecomax.get_value(ATTR_SCHEDULES))["heating"]
    schedule_switch = await ecomax.get_parameter("schedule_heating_switch")
    schedule_parameter = await ecomax.get_parameter("schedule_heating_parameter")
    assert isinstance(schedule, Schedule)
    assert schedule_switch.value == 0
    assert isinstance(schedule_switch, ScheduleBinaryParameter)
    assert schedule_parameter.value == 5
    assert schedule_parameter.min_value == 0
    assert schedule_parameter.max_value == 30
    assert isinstance(schedule_parameter, ScheduleParameter)
    schedule_data = data[FrameType.RESPONSE_SCHEDULES][ATTR_SCHEDULES]["heating"]
    assert schedule.sunday.intervals == schedule_data[ATTR_SCHEDULE][0]


async def test_deprecated(ecomax: EcoMAX) -> None:
    """Test deprecated function warnings."""
    mock_callback = AsyncMock(return_value=None)
    deprecated: Tuple[str, ...] = ()

    for func_name in deprecated:
        with warnings.catch_warnings(record=True) as warn:
            func = getattr(ecomax, func_name)
            warnings.simplefilter("always")
            func("test_sensor", mock_callback)
            assert len(warn) == 1
            assert issubclass(warn[-1].category, DeprecationWarning)
            assert "deprecated" in str(warn[-1].message)


async def test_subscribe(ecomax: EcoMAX) -> None:
    """Test callback registration."""
    mock_callback = AsyncMock(return_value=None)
    ecomax.subscribe("test_sensor", mock_callback)
    ecomax.handle_frame(Response(data={ATTR_ECOMAX_SENSORS: {"test_sensor": 42.1}}))
    await ecomax.wait_until_done()
    mock_callback.assert_awaited_once_with(42.1)
    mock_callback.reset_mock()

    # Test with change.
    ecomax.handle_frame(Response(data={ATTR_ECOMAX_SENSORS: {"test_sensor": 45}}))
    await ecomax.wait_until_done()
    mock_callback.assert_awaited_once_with(45)
    mock_callback.reset_mock()

    # Remove the callback and make sure it doesn't fire again.
    ecomax.unsubscribe("test_sensor", mock_callback)
    ecomax.handle_frame(Response(data={ATTR_ECOMAX_SENSORS: {"test_sensor": 50}}))
    await ecomax.wait_until_done()
    mock_callback.assert_not_awaited()


async def test_get_value(ecomax: EcoMAX) -> None:
    """Test wait for device method."""
    mock_event = Mock(spec=asyncio.Event)
    with pytest.raises(KeyError), patch(
        "pyplumio.devices.BaseDevice.create_event", return_value=mock_event
    ) as mock_create_event:
        mock_event.wait = AsyncMock()
        await ecomax.get_value("foo")

    mock_create_event.assert_called_once_with("foo")
    mock_event.wait.assert_awaited_once()


async def test_set_value(ecomax: EcoMAX) -> None:
    """Test setting parameter value via set_value helper."""
    # Test with valid parameter.
    mock_event = Mock(spec=asyncio.Event)
    with pytest.raises(KeyError), patch(
        "pyplumio.devices.BaseDevice.create_event", return_value=mock_event
    ) as mock_create_event:
        mock_event.wait = AsyncMock()
        await ecomax.set_value("foo", 1)

    mock_create_event.assert_called_once_with("foo")
    mock_event.wait.assert_awaited_once()
    ecomax.data["foo"] = Mock(spec=Parameter)
    await ecomax.set_value("foo", 2)
    ecomax.data["foo"].set.assert_called_once_with(2)

    # Test without blocking.
    with patch(
        "pyplumio.helpers.task_manager.TaskManager.create_task"
    ) as mock_create_task:
        await ecomax.set_value("foo", 2, await_confirmation=False)
        mock_create_task.assert_called_once()

    # Test with invalid parameter.
    ecomax.data["bar"] = Mock()
    with pytest.raises(ParameterNotFoundError):
        await ecomax.set_value("bar", 1)


async def test_get_parameter(ecomax: EcoMAX) -> None:
    """Test getting parameter from device."""
    mock_event = Mock(spec=asyncio.Event)
    with pytest.raises(KeyError), patch(
        "pyplumio.devices.BaseDevice.create_event", return_value=mock_event
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
@patch("pyplumio.devices.BaseDevice.cancel_tasks")
@patch("pyplumio.devices.BaseDevice.wait_until_done")
async def test_shutdown(
    mock_wait_until_done,
    mock_cancel_tasks,
    mock_thermostat_shutdown,
    mock_mixer_shutdown,
    ecomax: EcoMAX,
) -> None:
    """Test device tasks shutdown."""
    ecomax.handle_frame(Response(data={ATTR_MIXER_SENSORS: [(0, {"test_sensor": 42})]}))
    ecomax.handle_frame(
        Response(data={ATTR_THERMOSTAT_SENSORS: [(0, {"test_sensors": 42})]})
    )
    await ecomax.get_value(ATTR_MIXERS)
    await ecomax.get_value(ATTR_THERMOSTATS)
    await ecomax.shutdown()
    mock_wait_until_done.assert_awaited_once()
    mock_cancel_tasks.assert_called_once()
    mock_thermostat_shutdown.assert_awaited_once()
    mock_mixer_shutdown.assert_awaited_once()
