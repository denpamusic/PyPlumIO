import pytest

from pyplumio.helpers.parameter import Parameter


@pytest.fixture
def parameter() -> Parameter:
    return Parameter(name="AUTO_SUMMER", value=1, min_=0, max_=1)


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
    name = AUTO_SUMMER,
    value = 1,
    min_ = 0,
    max_ = 1,
    extra = None
)""".strip()

    assert repr(parameter) == output


def test_parameter__str__(parameter: Parameter):
    assert str(parameter) == "AUTO_SUMMER: 1 (range 0 - 1)"
