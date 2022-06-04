"""Test PyPlumIO mixers."""

import pytest

from pyplumio.constants import BROADCAST_ADDRESS
from pyplumio.frames.requests import SetMixerParameter
from pyplumio.mixers import Mixer, MixerCollection
from pyplumio.structures.mixer_parameters import MIXER_PARAMETERS

_test_data = {
    "temp": 40,
    "target": 60,
    "pump": True,
}

_test_data2 = {
    "temp": 45,
    "target": 60,
    "pump": True,
}

_test_parameters = {
    "mix_target_temp": [60, 40, 80],
}

_test_parameters2 = {
    "mix_target_temp": [65, 40, 80],
}


@pytest.fixture(name="mixer_with_data")
def fixture_mixer_with_data(mixer: Mixer) -> Mixer:
    mixer.set_data(_test_data)
    mixer.set_parameters(_test_parameters)
    return mixer


@pytest.fixture(name="mixers")
def fixture_mixers(mixer_with_data: Mixer) -> MixerCollection:
    return MixerCollection(mixers=[mixer_with_data])


def test_set_data(mixer: Mixer) -> None:
    """Test setting mixer data."""
    mixer.set_data(_test_data)
    assert mixer.temp == 40


def test_set_parameters(mixer: Mixer) -> None:
    """Test setting mixer parameters."""
    mixer.set_parameters(_test_parameters)
    assert mixer.mix_target_temp == 60


def test_editable_parameters(mixer: Mixer) -> None:
    """Test getting editable parameters."""
    assert mixer.editable_parameters == MIXER_PARAMETERS


def test_collection_repr(mixers: MixerCollection) -> None:
    """Test mixers collection serializable interpretation."""
    assert """
MixerCollection(
    address = 0,
    mixers = [Mixer(
    data = {'temp': 40, 'target': 60, 'pump': True},
    parameters = {'mix_target_temp': Parameter(
    name = mix_target_temp,
    value = 60,
    min_value = 40,
    max_value = 80,
    extra = 0
)}
    index  = 0
)]
)
""".strip() == repr(
        mixers
    )


def test_collection_str(mixers: MixerCollection) -> None:
    """Test mixers collection string representation."""
    assert """
- 0:
    Data:
    - temp: 40
    - target: 60
    - pump: True

    Parameters:
    - mix_target_temp: 60 (range 40 - 80)
""".strip() == str(
        mixers
    )


def test_collection_len(mixers: MixerCollection) -> None:
    """Test getting mixers collection length."""
    assert len(mixers) == 1


def test_collection_call(mixers: MixerCollection) -> None:
    """Test getting mixer from collection via instance call."""
    assert mixers(0).mix_target_temp == 60


def test_collection_call_nonexistent(mixers: MixerCollection) -> None:
    """Test getting nonexistent mixer from collection via call."""
    assert mixers(39) is None


def test_collection_set_data(mixers: MixerCollection) -> None:
    """Test setting collection data."""
    mixers.set_data([_test_data2])
    assert mixers(0).temp == 45


def test_collection_set_data_for_unknown_mixer(mixers: MixerCollection) -> None:
    """Test setting data for unknown mixer."""
    mixers.set_data([_test_data, _test_data2])
    assert mixers(0).temp == 40
    assert mixers(1).temp == 45


def test_collection_set_parameters(mixers: MixerCollection) -> None:
    """Test setting mixer parameters."""
    mixers.set_parameters([_test_parameters2])
    assert mixers(0).mix_target_temp == 65


def test_collection_set_parameters_from_unknown_mixer(mixers: MixerCollection) -> None:
    """Test setting parameters for unknown mixer."""
    mixers.set_parameters([_test_parameters, _test_parameters2])
    assert mixers(0).mix_target_temp == 60
    assert mixers(1).mix_target_temp == 65


def test_collection_get_mixers(mixers: MixerCollection) -> None:
    """Test get mixers from the list."""
    mixers.set_parameters([_test_parameters, _test_parameters2])
    assert mixers.mixers[0].mix_target_temp == 60
    assert mixers.mixers[1].mix_target_temp == 65


def test_collection_queue(mixers: MixerCollection) -> None:
    """Test changed parameters queue."""
    mixers(0).mix_target_temp = 65
    request = mixers.queue[0]
    assert isinstance(request, SetMixerParameter)
    assert request.recipient == BROADCAST_ADDRESS
    assert request.data["value"] == 65
