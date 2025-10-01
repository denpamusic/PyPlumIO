"""Contains tests for the mixer virtual device."""

import asyncio
import logging
from typing import Final

import pytest

from pyplumio.const import ATTR_SENSORS
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.devices.mixer import Mixer
from pyplumio.frames.messages import SensorDataMessage
from pyplumio.frames.responses import MixerParametersResponse
from pyplumio.parameters import ParameterValues
from pyplumio.parameters.mixer import MixerNumber, MixerParameter, MixerSwitch
from pyplumio.structures.mixer_parameters import ATTR_MIXER_PARAMETERS
from pyplumio.structures.sensor_data import ATTR_MIXER_SENSORS
from tests.conftest import class_from_json

MIXER_INDEX: Final = 4


@pytest.fixture(name="mixer")
def fixture_mixer(ecomax: EcoMAX) -> Mixer:
    """Return a Mixer object."""
    return Mixer(asyncio.Queue(), parent=ecomax, index=MIXER_INDEX)


@class_from_json(SensorDataMessage, "messages/sensor_data.json", arguments=("message",))
async def test_mixer_sensors_event_listener(
    mixer: Mixer, sensor_data: SensorDataMessage
) -> None:
    """Test event listener for mixer sensors."""
    mixer_sensors_data = sensor_data.data[ATTR_SENSORS][ATTR_MIXER_SENSORS]
    mixer.dispatch_nowait(ATTR_MIXER_SENSORS, mixer_sensors_data[MIXER_INDEX])
    await mixer.wait_until_done()
    assert mixer.data == {
        "current_temp": 20.0,
        "target_temp": 40,
        "pump": False,
        "mixer_sensors": True,
    }


@class_from_json(
    MixerParametersResponse,
    "responses/mixer_parameters.json",
    arguments=("message",),
)
@pytest.mark.parametrize(
    ("name", "cls", "values"),
    [
        (
            "mixer_target_temp",
            MixerNumber,
            ParameterValues(value=40, min_value=30, max_value=60),
        ),
        (
            "min_target_temp",
            MixerNumber,
            ParameterValues(value=20, min_value=30, max_value=40),
        ),
        (
            "max_target_temp",
            MixerNumber,
            ParameterValues(value=80, min_value=70, max_value=90),
        ),
        (
            "thermostat_decrease_target_temp",
            MixerNumber,
            ParameterValues(value=20, min_value=10, max_value=30),
        ),
        (
            "weather_control",
            MixerSwitch,
            ParameterValues(value=1, min_value=0, max_value=1),
        ),
        (
            "heating_curve",
            MixerNumber,
            ParameterValues(value=13, min_value=10, max_value=30),
        ),
    ],
)
async def test_mixer_parameters_event_listener(
    mixer: Mixer,
    mixer_parameters: MixerParametersResponse,
    name: str,
    cls: type[MixerParameter],
    values: ParameterValues,
) -> None:
    """Test event listener for mixer parameters."""
    mixer_parameters_data = mixer_parameters.data[ATTR_MIXER_PARAMETERS]
    mixer.dispatch_nowait(ATTR_MIXER_PARAMETERS, mixer_parameters_data[0])
    await mixer.wait_until_done()
    assert len(mixer.data) == 7
    parameter = mixer.get_nowait(name)
    assert isinstance(parameter, cls)
    assert parameter.values == values


@class_from_json(
    MixerParametersResponse,
    "unknown/unknown_mixer_parameter.json",
    arguments=("message",),
)
async def test_mixer_parameters_event_listener_unknown_parameter(
    mixer: Mixer, unknown_mixer_parameter: MixerParametersResponse, caplog
) -> None:
    """Test unknown mixer parameter."""
    mixer_parameters_data = unknown_mixer_parameter.data[ATTR_MIXER_PARAMETERS]
    with caplog.at_level(logging.WARNING):
        mixer.dispatch_nowait(ATTR_MIXER_PARAMETERS, mixer_parameters_data[0])
        await mixer.wait_until_done()

    assert "unknown mixer parameter (14)" in caplog.text
    assert "ParameterValues(value=1, min_value=1, max_value=1)" in caplog.text
    assert "ecoMAX 350P2-ZF" in caplog.text
