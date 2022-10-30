"""Contains tests for devices."""

import asyncio
from typing import Dict
from unittest.mock import AsyncMock, Mock, call, patch
import warnings

import pytest

from pyplumio.const import (
    ATTR_BOILER_PARAMETERS,
    ATTR_BOILER_SENSORS,
    ATTR_FUEL_BURNED,
    ATTR_FUEL_CONSUMPTION,
    ATTR_MIXER_PARAMETERS,
    ATTR_MIXER_SENSORS,
    ATTR_MODE,
    ATTR_REGDATA,
    ATTR_SCHEDULE,
    ATTR_SCHEDULES,
)
from pyplumio.devices import DeviceTypes, FrameVersions, Mixer, get_device_handler
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.devices.ecoster import EcoSTER
from pyplumio.exceptions import ParameterNotFoundError, UnknownDeviceError
from pyplumio.frames import FrameTypes, Response
from pyplumio.frames.messages import RegulatorDataMessage
from pyplumio.frames.requests import (
    AlertsRequest,
    BoilerParametersRequest,
    DataSchemaRequest,
    MixerParametersRequest,
    PasswordRequest,
    SchedulesRequest,
    StartMasterRequest,
    UIDRequest,
)
from pyplumio.frames.responses import DataSchemaResponse
from pyplumio.helpers.frame_versions import DEFAULT_FRAME_VERSION
from pyplumio.helpers.parameter import (
    BoilerBinaryParameter,
    MixerBinaryParameter,
    MixerParameter,
    Parameter,
    ScheduleBinaryParameter,
    ScheduleParameter,
)
from pyplumio.helpers.schedule import Schedule
from pyplumio.helpers.typing import DeviceDataType

UNKNOWN_DEVICE: int = 99
UNKNOWN_FRAME: int = 99


def test_device_handler() -> None:
    """Test getting device handler class by device address."""
    cls = get_device_handler(DeviceTypes.ECOMAX)
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
                FrameTypes.REQUEST_START_MASTER: DEFAULT_FRAME_VERSION,
                UNKNOWN_FRAME: DEFAULT_FRAME_VERSION,
            }
        )
        await versions.async_update(
            {int(x): DEFAULT_FRAME_VERSION for x in ecomax.required_frames}
        )

    calls = [
        call(StartMasterRequest(recipient=DeviceTypes.ECOMAX)),
        call(UIDRequest(recipient=DeviceTypes.ECOMAX)),
        call(DataSchemaRequest(recipient=DeviceTypes.ECOMAX)),
        call(BoilerParametersRequest(recipient=DeviceTypes.ECOMAX)),
        call(MixerParametersRequest(recipient=DeviceTypes.ECOMAX)),
        call(PasswordRequest(recipient=DeviceTypes.ECOMAX)),
        call(AlertsRequest(recipient=DeviceTypes.ECOMAX)),
        call(SchedulesRequest(recipient=DeviceTypes.ECOMAX)),
    ]
    mock_put_nowait.assert_has_calls(calls)
    assert versions.versions == {
        0x19: 0,
        0x39: 0,
        0x3A: 0,
        0x55: 0,
        0x31: 0,
        0x32: 0,
        0x3D: 0,
        0x36: 0,
    }


async def test_boiler_data_callbacks(ecomax: EcoMAX) -> None:
    """Test callbacks that are fired on received data frames."""
    frames = (
        Response(data={ATTR_BOILER_SENSORS: {"test_sensor": 42}}),
        Response(data={ATTR_MODE: 1}),
    )
    for frame in frames:
        ecomax.handle_frame(frame)

    assert await ecomax.get_value("test_sensor") == 42
    boiler_control = await ecomax.get_parameter("boiler_control")
    assert isinstance(boiler_control, BoilerBinaryParameter)
    assert boiler_control.value == 1


async def test_boiler_parameters_callbacks(ecomax: EcoMAX) -> None:
    """Test callbacks that are fired on received parameter frames."""
    ecomax.handle_frame(
        Response(
            data={
                ATTR_BOILER_PARAMETERS: {
                    "test_binary_parameter": [0, 0, 1],
                    "test_parameter": [10, 5, 20],
                }
            }
        )
    )

    assert await ecomax.get_value("test_binary_parameter") == 0
    test_binary_parameter = await ecomax.get_parameter("test_binary_parameter")
    assert isinstance(test_binary_parameter, BoilerBinaryParameter)
    assert await ecomax.get_value("test_parameter") == 10
    test_parameter = await ecomax.get_parameter("test_parameter")
    assert test_parameter.value == 10
    assert test_parameter.min_value == 5
    assert test_parameter.max_value == 20


async def test_fuel_consumption_callbacks() -> None:
    """Test callbacks that are fired on received fuel consumption."""

    with patch("time.time", side_effect=(10, 20)):
        ecomax = EcoMAX(asyncio.Queue())
        ecomax.handle_frame(Response(data={ATTR_FUEL_CONSUMPTION: 3.6}))
        await ecomax.wait_until_done()

    assert await ecomax.get_value(ATTR_FUEL_BURNED) == 0.01


async def test_regdata_callbacks(
    ecomax: EcoMAX, messages: Dict[int, bytearray]
) -> None:
    """Test callbacks that are fired on received regdata."""
    # Test exception handling on data schema timeout.
    with patch(
        "pyplumio.devices.AsyncDevice.get_value", side_effect=asyncio.TimeoutError
    ):
        ecomax.handle_frame(
            RegulatorDataMessage(message=messages[FrameTypes.MESSAGE_REGULATOR_DATA])
        )
        await ecomax.wait_until_done()

    # Regulator data should be empty on schema timeout.
    assert not await ecomax.get_value(ATTR_REGDATA)

    # Set data schema and decode the regdata.
    ecomax.handle_frame(
        DataSchemaResponse(message=messages[FrameTypes.RESPONSE_DATA_SCHEMA])
    )
    ecomax.handle_frame(
        RegulatorDataMessage(message=messages[FrameTypes.MESSAGE_REGULATOR_DATA])
    )
    await ecomax.wait_until_done()

    regdata = await ecomax.get_value(ATTR_REGDATA)
    assert regdata["mode"] == 0
    assert round(regdata["heating_temp"], 1) == 22.4
    assert regdata["heating_target"] == 41
    assert regdata["183"] == "0.0.0.0"
    assert regdata["184"] == "255.255.255.0"


async def test_mixer_sensors_callbacks(ecomax: EcoMAX) -> None:
    """Test callbacks that are fired on receiving mixer sensors info."""
    ecomax.handle_frame(Response(data={ATTR_MIXER_SENSORS: [{"test_sensor": 42}]}))
    mixers = await ecomax.get_value("mixers")
    assert len(mixers) == 1
    assert isinstance(mixers[0], Mixer)
    assert mixers[0].index == 0
    assert await mixers[0].get_value("test_sensor") == 42


async def test_mixer_parameters_callbacks(ecomax: EcoMAX) -> None:
    """Test callbacks that are fired on receiving mixer parameters."""
    ecomax.handle_frame(
        Response(
            data={
                ATTR_MIXER_PARAMETERS: [
                    {
                        "test_binary_parameter": [0, 0, 1],
                        "test_parameter": [10, 5, 20],
                    }
                ]
            }
        )
    )
    mixers = await ecomax.get_value("mixers")
    test_binary_parameter = await mixers[0].get_parameter("test_binary_parameter")
    assert test_binary_parameter.value == 0
    assert isinstance(test_binary_parameter, MixerBinaryParameter)
    test_parameter = await mixers[0].get_parameter("test_parameter")
    assert isinstance(test_parameter, MixerParameter)
    assert test_parameter.value == 10
    assert test_parameter.min_value == 5
    assert test_parameter.max_value == 20


async def test_schedule_callback(
    ecomax: EcoMAX, data: Dict[int, DeviceDataType]
) -> None:
    """Test callback that is fired on receiving schedule data."""
    ecomax.handle_frame(Response(data=data[FrameTypes.RESPONSE_SCHEDULES]))
    schedule = (await ecomax.get_value("schedules"))["heating"]
    schedule_switch = await ecomax.get_parameter("schedule_heating_switch")
    schedule_parameter = await ecomax.get_parameter("schedule_heating_parameter")
    assert isinstance(schedule, Schedule)
    assert schedule_switch.value == 0
    assert isinstance(schedule_switch, ScheduleBinaryParameter)
    assert schedule_parameter.value == 5
    assert schedule_parameter.min_value == 0
    assert schedule_parameter.max_value == 30
    assert isinstance(schedule_parameter, ScheduleParameter)
    schedule_data = data[FrameTypes.RESPONSE_SCHEDULES][ATTR_SCHEDULES]["heating"]
    assert schedule.sunday.intervals == schedule_data[ATTR_SCHEDULE][0]


async def test_deprecated(ecomax: EcoMAX) -> None:
    """Test deprecated function warnings."""
    mock_callback = AsyncMock(return_value=None)
    deprecated = (
        "register_callback",
        "remove_callback",
    )

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
    ecomax.handle_frame(Response(data={ATTR_BOILER_SENSORS: {"test_sensor": 42.1}}))
    await ecomax.wait_until_done()
    mock_callback.assert_awaited_once_with(42.1)
    mock_callback.reset_mock()

    # Test with change.
    ecomax.handle_frame(Response(data={ATTR_BOILER_SENSORS: {"test_sensor": 45}}))
    await ecomax.wait_until_done()
    mock_callback.assert_awaited_once_with(45)
    mock_callback.reset_mock()

    # Remove the callback and make sure it doesn't fire again.
    ecomax.unsubscribe("test_sensor", mock_callback)
    ecomax.handle_frame(Response(data={ATTR_BOILER_SENSORS: {"test_sensor": 50}}))
    await ecomax.wait_until_done()
    mock_callback.assert_not_awaited()


async def test_get_value(ecomax: EcoMAX) -> None:
    """Test wait for device method."""
    mock_event = Mock(spec=asyncio.Event)
    with pytest.raises(KeyError), patch(
        "pyplumio.devices.AsyncDevice.create_event", return_value=mock_event
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
        "pyplumio.devices.AsyncDevice.create_event", return_value=mock_event
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
        await ecomax.set_value("foo", 2, block=False)
        mock_create_task.assert_called_once()

    # Test with invalid parameter.
    ecomax.data["bar"] = Mock()
    with pytest.raises(ParameterNotFoundError):
        await ecomax.set_value("bar", 1)


async def test_get_parameter(ecomax: EcoMAX) -> None:
    """Test getting parameter from device."""
    mock_event = Mock(spec=asyncio.Event)
    with pytest.raises(KeyError), patch(
        "pyplumio.devices.AsyncDevice.create_event", return_value=mock_event
    ) as mock_create_event:
        mock_event.wait = AsyncMock()
        await ecomax.get_parameter("foo")

    mock_create_event.assert_called_once_with("foo")
    mock_event.wait.assert_awaited_once()

    # Test with invalid parameter.
    ecomax.data["bar"] = Mock()
    with pytest.raises(ParameterNotFoundError):
        await ecomax.get_parameter("bar")


@patch("pyplumio.devices.Mixer.shutdown")
@patch("pyplumio.devices.AsyncDevice.cancel_tasks")
@patch("pyplumio.devices.AsyncDevice.wait_until_done")
async def test_shutdown(
    mock_wait_until_done, mock_cancel_tasks, mock_shutdown, ecomax: EcoMAX
) -> None:
    """Test device tasks shutdown."""
    ecomax.handle_frame(Response(data={ATTR_MIXER_SENSORS: [{"test_sensor": 42}]}))
    await ecomax.get_value("mixers")
    await ecomax.shutdown()
    mock_wait_until_done.assert_awaited_once()
    mock_cancel_tasks.assert_called_once()
    mock_shutdown.assert_awaited_once()
