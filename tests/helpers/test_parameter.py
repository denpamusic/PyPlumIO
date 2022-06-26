"""Contains test for Parameter class."""

import asyncio

import pytest

from pyplumio.constants import BROADCAST_ADDRESS, STATE_OFF
from pyplumio.frames.requests import (
    BoilerControl,
    SetBoilerParameter,
    SetMixerParameter,
)
from pyplumio.helpers.parameter import BoilerParameter, MixerParameter


@pytest.fixture(name="parameter")
def fixture_parameter() -> BoilerParameter:
    """Returns instance of auto_summer parameter."""
    return BoilerParameter(
        queue=asyncio.Queue(),
        recipient=BROADCAST_ADDRESS,
        name="auto_summer",
        value=1,
        min_value=0,
        max_value=1,
    )


def test_parameter_set(parameter: BoilerParameter) -> None:
    """Test setting parameter."""
    parameter.set(0)
    assert parameter == STATE_OFF


def test_parameter_set_out_of_range(parameter: BoilerParameter) -> None:
    """Test setting parameter with value out of allowed range."""
    with pytest.raises(ValueError):
        parameter.set(39)


def test_parameter_compare(parameter: BoilerParameter) -> None:
    """Test parameter comparison."""
    assert parameter == 1
    assert parameter < 2
    assert parameter > 0
    assert 0 <= parameter <= 1


def test_parameter_int(parameter: BoilerParameter) -> None:
    """Test conversion to integer."""
    assert int(parameter) == 1


def test_parameter__repr__(parameter: BoilerParameter) -> None:
    """Test parameter serilizable representation."""
    output = f"""BoilerParameter(
    queue = asyncio.Queue(),
    recipient = {BROADCAST_ADDRESS},
    name = auto_summer,
    value = 1,
    min_value = 0,
    max_value = 1,
    extra = None
)""".strip()

    assert repr(parameter) == output


def test_parameter_request(parameter: BoilerParameter) -> None:
    """Test parameter set request instance."""
    assert isinstance(parameter.request, SetBoilerParameter)


def test_parameter_request_mixer() -> None:
    """Test set mixer parameter request instance."""
    parameter = MixerParameter(
        queue=asyncio.Queue(),
        recipient=BROADCAST_ADDRESS,
        name="mix_target_temp",
        value=50,
        min_value=50,
        max_value=80,
        extra=0,
    )
    assert isinstance(parameter.request, SetMixerParameter)


def test_parameter_request_control() -> None:
    """Test boiler control parameter request instance."""
    parameter = BoilerParameter(
        queue=asyncio.Queue(),
        recipient=BROADCAST_ADDRESS,
        name="boiler_control",
        value=1,
        min_value=0,
        max_value=1,
    )
    assert isinstance(parameter.request, BoilerControl)
