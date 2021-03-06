"""Contains tests for devices."""

import asyncio
from typing import Dict
from unittest.mock import AsyncMock, Mock, call, patch

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
    ECOMAX_ADDRESS,
)
from pyplumio.devices import EcoMAX, FrameVersions, Mixer, get_device_handler
from pyplumio.exceptions import ParameterNotFoundError, UnknownDeviceError
from pyplumio.frames import MessageTypes, Response, ResponseTypes
from pyplumio.frames.messages import RegulatorDataMessage
from pyplumio.frames.requests import (
    AlertsRequest,
    BoilerParametersRequest,
    DataSchemaRequest,
    MixerParametersRequest,
    PasswordRequest,
    StartMasterRequest,
    UIDRequest,
)
from pyplumio.frames.responses import DataSchemaResponse
from pyplumio.helpers.parameter import (
    BoilerBinaryParameter,
    MixerBinaryParameter,
    MixerParameter,
    Parameter,
)

UNKNOWN_DEVICE: int = 99


@pytest.fixture(name="ecomax")
def fixture_ecomax() -> EcoMAX:
    """Return ecomax device instance."""
    return EcoMAX(asyncio.Queue())


def test_device_handler() -> None:
    """Test getting device handler class by device address."""
    cls = get_device_handler(ECOMAX_ADDRESS)
    assert cls == "devices.EcoMAX"
    with pytest.raises(UnknownDeviceError):
        cls = get_device_handler(UNKNOWN_DEVICE)


UNKNOWN_FRAME: int = 99


async def test_frame_versions_update(ecomax: EcoMAX) -> None:
    """Test requesting updated frames."""
    versions = FrameVersions(ecomax.queue, ecomax)
    with patch("asyncio.Queue.put_nowait") as mock_put_nowait:
        await versions.async_update({0x19: 0, UNKNOWN_FRAME: 0})
        await versions.async_update({x.frame_type: 0 for x in ecomax.required_frames})

    calls = [
        call(StartMasterRequest(recipient=ECOMAX_ADDRESS)),
        call(UIDRequest(recipient=ECOMAX_ADDRESS)),
        call(DataSchemaRequest(recipient=ECOMAX_ADDRESS)),
        call(BoilerParametersRequest(recipient=ECOMAX_ADDRESS)),
        call(MixerParametersRequest(recipient=ECOMAX_ADDRESS)),
        call(PasswordRequest(recipient=ECOMAX_ADDRESS)),
        call(AlertsRequest(recipient=ECOMAX_ADDRESS)),
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
            RegulatorDataMessage(message=messages[MessageTypes.REGULATOR_DATA])
        )
        await ecomax.wait_until_done()

    # Regulator data should be empty on schema timeout.
    assert not await ecomax.get_value(ATTR_REGDATA)

    # Set data schema and decode the regdata.
    ecomax.handle_frame(DataSchemaResponse(message=messages[ResponseTypes.DATA_SCHEMA]))
    ecomax.handle_frame(
        RegulatorDataMessage(message=messages[MessageTypes.REGULATOR_DATA])
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


async def test_register_callback(ecomax: EcoMAX) -> None:
    """Test callback registration."""
    mock_callback = AsyncMock(return_value=None)
    ecomax.register_callback("test_sensor", mock_callback)
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
    ecomax.remove_callback("test_sensor", mock_callback)
    ecomax.handle_frame(Response(data={ATTR_BOILER_SENSORS: {"test_sensor": 50}}))
    await ecomax.wait_until_done()
    mock_callback.assert_not_awaited()


async def test_get_value(ecomax: EcoMAX) -> None:
    """Test wait for device method."""
    mock_event = Mock(spec=asyncio.Event)
    with pytest.raises(AttributeError), patch(
        "pyplumio.devices.AsyncDevice.create_event", return_value=mock_event
    ) as mock_create_event:
        mock_event.wait = AsyncMock()
        await ecomax.get_value("valid_value")

    mock_create_event.assert_called_once_with("valid_value")
    mock_event.wait.assert_awaited_once()


async def test_set_value(ecomax: EcoMAX) -> None:
    """Test setting parameter value via set_value helper."""
    # Test with valid parameter.
    mock_valid = Mock(spec=Parameter)
    mock_event = Mock(spec=asyncio.Event)
    with pytest.raises(AttributeError), patch(
        "pyplumio.devices.AsyncDevice.create_event", return_value=mock_event
    ) as mock_create_event:
        mock_event.wait = AsyncMock()
        await ecomax.set_value("valid_parameter", 1)

    mock_create_event.assert_called_once_with("valid_parameter")
    mock_event.wait.assert_awaited_once()
    ecomax.__dict__["valid_parameter"] = mock_valid
    await ecomax.set_value("valid_parameter", 2)
    mock_valid.set.assert_called_once_with(2)

    # Test with invalid parameter.
    mock_invalid = Mock()
    ecomax.__dict__["invalid_parameter"] = mock_invalid
    with pytest.raises(ParameterNotFoundError):
        await ecomax.set_value("invalid_parameter", 1)


async def test_get_parameter(ecomax: EcoMAX) -> None:
    """Test getting parameter from device."""
    mock_event = Mock(spec=asyncio.Event)
    with pytest.raises(AttributeError), patch(
        "pyplumio.devices.AsyncDevice.create_event", return_value=mock_event
    ) as mock_create_event:
        mock_event.wait = AsyncMock()
        await ecomax.get_parameter("test_parameter")

    mock_create_event.assert_called_once_with("test_parameter")
    mock_event.wait.assert_awaited_once()

    # Test with invalid parameter.
    invalid = Mock()
    ecomax.__dict__["invalid_parameter"] = invalid
    with pytest.raises(ParameterNotFoundError):
        await ecomax.get_parameter("invalid_parameter")


@patch("pyplumio.devices.Mixer.shutdown")
@patch("pyplumio.devices.AsyncDevice.cancel_tasks")
@patch("pyplumio.devices.AsyncDevice.wait_until_done")
async def test_shutdown(
    mock_wait_until_done, mock_cancel_tasks, mock_shutdown, ecomax: EcoMAX
) -> None:
    """Test device tasks shutdown."""
    ecomax.handle_frame(Response(data={ATTR_MIXER_SENSORS: [{"test_sensor": 42}]}))
    await ecomax.shutdown()
    mock_wait_until_done.assert_awaited_once()
    mock_cancel_tasks.assert_called_once()
    mock_shutdown.assert_awaited_once()
