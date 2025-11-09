"""Contains tests for the mixer parameter descriptors."""

import asyncio

import pytest

from pyplumio.const import ATTR_DEVICE_INDEX, ATTR_INDEX, ATTR_VALUE, ProductType
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.devices.mixer import Mixer
from pyplumio.frames.requests import SetMixerParameterRequest
from pyplumio.parameters import ParameterValues
from pyplumio.parameters.mixer import (
    PARAMETER_TYPES as MIXER_PARAMETER_TYPE,
    MixerNumber,
    MixerNumberDescription,
    MixerSwitch,
    MixerSwitchDescription,
    get_mixer_parameter_types,
)


@pytest.fixture(name="mixer")
def fixture_mixer(ecomax: EcoMAX) -> Mixer:
    """Return an mixer object."""
    return Mixer(asyncio.Queue(), parent=ecomax)


async def test_mixer_parameter_create_request(mixer: Mixer) -> None:
    """Test create_request method for mixer parameter."""
    # Test with number.
    mixer_number = MixerNumber(
        device=mixer,
        description=MixerNumberDescription(name="test_number"),
        values=ParameterValues(value=10, min_value=0, max_value=20),
    )
    mixer_number_request = await mixer_number.create_request()
    assert isinstance(mixer_number_request, SetMixerParameterRequest)
    assert mixer_number_request.data == {
        ATTR_INDEX: 0,
        ATTR_VALUE: 10,
        ATTR_DEVICE_INDEX: 0,
    }

    # Test with switch.
    mixer_switch = MixerSwitch(
        device=mixer,
        description=MixerSwitchDescription(name="test_switch"),
        values=ParameterValues(value=0, min_value=0, max_value=1),
    )
    mixer_switch_request = await mixer_switch.create_request()
    assert isinstance(mixer_switch_request, SetMixerParameterRequest)
    assert mixer_switch_request.data == {
        ATTR_INDEX: 0,
        ATTR_VALUE: 0,
        ATTR_DEVICE_INDEX: 0,
    }


def test_get_mixer_parameter_types(mixer: Mixer) -> None:
    """Test ecoMAX parameter types getter."""
    parameter_types = get_mixer_parameter_types(mixer.parent.product)
    assert len(MIXER_PARAMETER_TYPE[ProductType.ECOMAX_P]) == 14
    assert MIXER_PARAMETER_TYPE[ProductType.ECOMAX_P] == parameter_types
