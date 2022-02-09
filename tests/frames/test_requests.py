from pyplumio.frame import BROADCAST_ADDRESS, ECONET_ADDRESS
import pyplumio.frames.requests as requests
import pyplumio.frames.responses as responses


def test_base_class_response():
    assert requests.Request().response() is None


def test_request_type():
    for request in [
        requests.ProgramVersion,
        requests.CheckDevice,
        requests.UID,
        requests.Password,
        requests.Parameters,
        requests.MixerParameters,
        requests.DataStructure,
        requests.StartMaster,
        requests.StopMaster,
    ]:
        frame = request(recipient=BROADCAST_ADDRESS, sender=ECONET_ADDRESS)
        assert frame.is_type(request)


def test_program_version_response_recipient_and_type():
    frame = requests.ProgramVersion(recipient=BROADCAST_ADDRESS, sender=ECONET_ADDRESS)
    assert frame.response().is_type(responses.ProgramVersion)
    assert frame.response().recipient == ECONET_ADDRESS


def test_check_device_response_recipient_and_type():
    frame = requests.CheckDevice(recipient=BROADCAST_ADDRESS, sender=ECONET_ADDRESS)
    assert frame.response().is_type(responses.DeviceAvailable)
    assert frame.response().recipient == ECONET_ADDRESS


def test_parameters():
    frame = requests.Parameters()
    assert frame.bytes == b"\x68\x0c\x00\x00\x56\x30\x05\x31\xff\x00\xc9\x16"


def test_set_parameter():
    frame = requests.SetParameter(data={"name": "airflow_power_100", "value": 80})
    assert frame.bytes == b"\x68\x0c\x00\x00\x56\x30\x05\x33\x00\x50\x64\x16"


def test_set_mixer_parameter():
    frame = requests.SetMixerParameter(
        data={"name": "mix_set_temp", "value": 40, "extra": 0}
    )
    assert frame.bytes == b"\x68\x0d\x00\x00\x56\x30\x05\x34\x00\x00\x28\x1a\x16"


def test_boiler_control():
    frame = requests.BoilerControl(data={"value": 1})
    assert frame.bytes == b"\x68\x0b\x00\x00\x56\x30\x05\x3b\x01\x3a\x16"
