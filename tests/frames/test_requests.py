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
        requests.Timezones,
        requests.Parameters,
        requests.MixerParameters,
        requests.DataStructure,
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
