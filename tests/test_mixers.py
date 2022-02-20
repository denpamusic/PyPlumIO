import pytest

from pyplumio.constants import MIXER_PARAMS
from pyplumio.frame import BROADCAST_ADDRESS
from pyplumio.mixers import Mixer, MixersCollection
from pyplumio.requests import SetMixerParameter

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
    "mix_set_temp": [60, 40, 80],
}

_test_parameters2 = {
    "mix_set_temp": [65, 40, 80],
}


@pytest.fixture
def mixer() -> Mixer:
    return Mixer()


@pytest.fixture
def mixer_with_data() -> Mixer:
    return Mixer(data=_test_data, parameters=_test_parameters, index=0)


@pytest.fixture
def mixers(mixer_with_data: Mixer) -> MixersCollection:
    return MixersCollection(mixers=[mixer_with_data])


def test_set_data(mixer: Mixer):
    mixer.set_data(_test_data)
    assert mixer.temp == 40


def test_set_parameters(mixer: Mixer):
    mixer.set_parameters(_test_parameters)
    assert mixer.mix_set_temp == 60


def test_editable_parameters(mixer: Mixer):
    assert mixer.editable_parameters == MIXER_PARAMS


def test_collection_repr(mixers: MixersCollection):
    assert """
MixersCollection(
    address = 0,
    mixers = [Mixer(
    data = {'temp': 40, 'target': 60, 'pump': True},
    parameters = {'mix_set_temp': Parameter(
    name = mix_set_temp,
    value = 60,
    min_ = 40,
    max_ = 80,
    extra = 0
)}
    index  = 0
)]
)
""".strip() == repr(
        mixers
    )


def test_collection_str(mixers: MixersCollection):
    assert """
- 0:
    Data:
    - temp: 40
    - target: 60
    - pump: True

    Parameters:
    - mix_set_temp: 60 (range 40 - 80)
""".strip() == str(
        mixers
    )


def test_collection_len(mixers: MixersCollection):
    assert len(mixers) == 1


def test_collection_call(mixers: MixersCollection):
    assert mixers(0).mix_set_temp == 60


def test_collection_call_nonexistents(mixers: MixersCollection):
    assert mixers(39) is None


def test_collection_set_data(mixers: MixersCollection):
    mixers.set_data([_test_data2])
    assert mixers(0).temp == 45


def test_collection_set_data_for_unknown_mixer(mixers: MixersCollection):
    mixers.set_data([_test_data, _test_data2])
    assert mixers(0).temp == 40
    assert mixers(1).temp == 45


def test_collection_set_parameters(mixers: MixersCollection):
    mixers.set_parameters([_test_parameters2])
    assert mixers(0).mix_set_temp == 65


def test_collection_set_parameters_fro_unknown_mixer(mixers: MixersCollection):
    mixers.set_parameters([_test_parameters, _test_parameters2])
    assert mixers(0).mix_set_temp == 60
    assert mixers(1).mix_set_temp == 65


def test_collection_get_mixers(mixers: MixersCollection):
    mixers.set_parameters([_test_parameters, _test_parameters2])
    assert mixers.mixers[0].mix_set_temp == 60
    assert mixers.mixers[1].mix_set_temp == 65


def test_collection_queue(mixers: MixersCollection):
    mixers(0).mix_set_temp = 65
    request = mixers.queue[0]
    assert isinstance(request, SetMixerParameter)
    assert request.recipient == BROADCAST_ADDRESS
    assert request.data["value"] == 65
