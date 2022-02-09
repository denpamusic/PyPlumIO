import pytest

from pyplumio.frames.requests import BoilerControl, SetMixerParameter, SetParameter
from pyplumio.helpers.parameter import Parameter


@pytest.fixture
def parameter() -> Parameter:
    return Parameter(name="auto_summer", value=1, min_=0, max_=1)


def test_parameter_set(parameter: Parameter):
    parameter.set(0)
    assert parameter == 0


def test_parameter_set_out_of_range(parameter: Parameter):
    parameter.set(39)
    assert parameter == 1


def test_parameter_compare(parameter: Parameter):
    assert parameter == 1
    assert parameter < 2
    assert parameter > 0
    assert 0 <= parameter <= 1


def test_parameter__repr__(parameter: Parameter):
    output = """Parameter(
    name = auto_summer,
    value = 1,
    min_ = 0,
    max_ = 1,
    extra = None
)""".strip()

    assert repr(parameter) == output


def test_parameter__str__(parameter: Parameter):
    assert str(parameter) == "auto_summer: 1 (range 0 - 1)"


def test_parameter_request(parameter: Parameter):
    assert isinstance(parameter.request, SetParameter)


def test_parameter_request_mixer():
    parameter = Parameter(name="mix_set_temp", value=50, min_=50, max_=80, extra=0)
    assert isinstance(parameter.request, SetMixerParameter)


def test_parameter_request_control():
    parameter = Parameter(name="boiler_control", value=1, min_=0, max_=1)
    assert isinstance(parameter.request, BoilerControl)
