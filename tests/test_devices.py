"""Contains tests for devices module."""

import asyncio
from unittest.mock import AsyncMock, call, patch

import pytest

from pyplumio.const import (
    DATA_BOILER_PARAMETERS,
    DATA_BOILER_SENSORS,
    DATA_FUEL_CONSUMPTION,
    DATA_MODE,
    DATA_REGDATA,
    ECOMAX_ADDRESS,
)
from pyplumio.devices import EcoMAX, FrameVersions, get_device_handler
from pyplumio.exceptions import UnknownDeviceError
from pyplumio.frames import Response, requests
from pyplumio.frames.messages import RegulatorData
from pyplumio.frames.responses import DataSchema
from pyplumio.helpers.parameter import BoilerBinaryParameter

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
        await versions.update({0x19: 0, UNKNOWN_FRAME: 0})

    calls = [
        call(requests.StartMaster(recipient=ECOMAX_ADDRESS)),
        call(requests.UID(recipient=ECOMAX_ADDRESS)),
        call(requests.Password(recipient=ECOMAX_ADDRESS)),
        call(requests.DataSchema(recipient=ECOMAX_ADDRESS)),
        call(requests.BoilerParameters(recipient=ECOMAX_ADDRESS)),
        call(requests.MixerParameters(recipient=ECOMAX_ADDRESS)),
    ]
    mock_put_nowait.assert_has_calls(calls)
    assert versions.versions == {0x19: 0, 0x39: 0, 0x3A: 0, 0x55: 0, 0x31: 0, 0x32: 0}


async def test_boiler_data_callbacks(ecomax: EcoMAX) -> None:
    """Test callbacks that are fired on received data frames."""
    frames = (
        Response(data={DATA_BOILER_SENSORS: {"test_sensor": 42}}),
        Response(data={DATA_MODE: 1}),
    )
    for frame in frames:
        await ecomax.handle_frame(frame)

    assert await ecomax.get_value("test_sensor") == 42
    boiler_control = await ecomax.get_parameter("boiler_control")
    assert isinstance(boiler_control, BoilerBinaryParameter)
    assert boiler_control.value == 1


async def test_boiler_parameters_callbacks(ecomax: EcoMAX) -> None:
    """Test callbacks that are fired on received parameter frames."""
    await ecomax.handle_frame(
        Response(
            data={
                DATA_BOILER_PARAMETERS: {
                    "test_binary_parameter": [0, 0, 1],
                    "test_parameter": [10, 20, 5],
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
        await ecomax.handle_frame(Response(data={DATA_FUEL_CONSUMPTION: 3.6}))

    assert await ecomax.get_value("fuel_burned") == 0.01


async def test_regdata_callbacks(
    ecomax: EcoMAX, data_schema: DataSchema, regulator_data: RegulatorData
) -> None:
    """Test callbacks that are fired on received regdata."""
    # Set data schema and parse the regdata.
    await ecomax.handle_frame(data_schema)
    await ecomax.handle_frame(regulator_data)

    regdata = await ecomax.get_value(DATA_REGDATA)
    assert regdata["mode"] == 0
    assert round(regdata["heating_temp"], 1) == 22.4
    assert regdata["heating_target"] == 41
    assert regdata["183"] == "0.0.0.0"
    assert regdata["184"] == "255.255.255.0"


async def test_register_callback(ecomax: EcoMAX) -> None:
    """Test callback registration."""
    mock_callback = AsyncMock(return_value=None)
    ecomax.register_callback(["test_sensor"], mock_callback)
    await ecomax.handle_frame(
        Response(data={DATA_BOILER_SENSORS: {"test_sensor": 42.1}})
    )
    mock_callback.assert_awaited_once_with(42.1)
    mock_callback.reset_mock()

    # Test with insignificant change.
    await ecomax.handle_frame(
        Response(data={DATA_BOILER_SENSORS: {"test_sensor": 42.11}})
    )
    mock_callback.assert_not_awaited()

    # Test with significant change.
    await ecomax.handle_frame(Response(data={DATA_BOILER_SENSORS: {"test_sensor": 45}}))
    mock_callback.assert_awaited_once_with(45)
