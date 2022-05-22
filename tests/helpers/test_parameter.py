"""Test PyPlumIO parameter helper."""

import pytest

from pyplumio.helpers.parameter import Parameter
from pyplumio.requests import BoilerControl, SetMixerParameter, SetParameter


@pytest.fixture(name="parameter")
def fixture_parameter() -> Parameter:
    """Returns instance of auto_summer parameter."""
    return Parameter(name="auto_summer", value=1, min_=0, max_=1)


def test_parameter_set(parameter: Parameter) -> None:
    """Test setting parameter."""
    parameter.set(0)
    assert parameter == 0


def test_parameter_set_out_of_range(parameter: Parameter) -> None:
    """Test setting parameter with value out of allowed range."""
    parameter.set(39)
    assert parameter == 1


def test_parameter_compare(parameter: Parameter) -> None:
    """Test parameter comparison."""
    assert parameter == 1
    assert parameter < 2
    assert parameter > 0
    assert 0 <= parameter <= 1


def test_parameter_int(parameter: Parameter) -> None:
    """Test conversion to integer."""
    assert int(parameter) == 1


def test_parameter__repr__(parameter: Parameter) -> None:
    """Test parameter serilizable representation."""
    output = """Parameter(
    name = auto_summer,
    value = 1,
    min_ = 0,
    max_ = 1,
    extra = None
)""".strip()

    assert repr(parameter) == output


def test_parameter__str__(parameter: Parameter) -> None:
    """Test parameter string representation."""
    assert str(parameter) == "auto_summer: 1 (range 0 - 1)"


def test_parameter_request(parameter: Parameter) -> None:
    """Test parameter set request instance."""
    assert isinstance(parameter.request, SetParameter)


def test_parameter_request_mixer() -> None:
    """Test set mixer parameter request instance."""
    parameter = Parameter(name="mix_set_temp", value=50, min_=50, max_=80, extra=0)
    assert isinstance(parameter.request, SetMixerParameter)


def test_parameter_request_control() -> None:
    """Test boiler control parameter request instance."""
    parameter = Parameter(name="boiler_control", value=1, min_=0, max_=1)
    assert isinstance(parameter.request, BoilerControl)
