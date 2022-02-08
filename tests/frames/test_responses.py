from pyplumio.frame import BROADCAST_ADDRESS, ECONET_ADDRESS
import pyplumio.frames.responses as responses


def test_responses_type():
    for response in [
        responses.ProgramVersion,
        responses.DeviceAvailable,
        responses.CurrentData,
        responses.UID,
        responses.Password,
        responses.Timezones,
        responses.Parameters,
        responses.MixerParameters,
        responses.DataStructure,
    ]:
        frame = response(recipient=BROADCAST_ADDRESS, sender=ECONET_ADDRESS)
        assert frame.is_type(response)


def test_program_version_create_message():
    data = {
        "version": "1.0.0",
        "struct_tag": b"\xFF\xFF",
        "struct_version": 5,
        "device_id": b"\x7A\x00",
        "processor_signature": b"\x00\x00\x00",
    }
    frame = responses.ProgramVersion(
        recipient=BROADCAST_ADDRESS, sender=ECONET_ADDRESS, data=data
    )
    message = frame.create_message()
    assert message == b"\xFF\xFF\x05\x7A\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x56"


def test_program_version_parse_message():
    frame = responses.ProgramVersion(recipient=BROADCAST_ADDRESS, sender=ECONET_ADDRESS)
    frame.parse_message(b"\xFF\xFF\x05\x7A\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x56")
    assert frame.data["version"] == "1.0.0"
    assert frame.data["struct_tag"] == b"\xFF\xFF"
    assert frame.data["struct_version"] == 5
    assert frame.data["device_id"] == b"\x7A\x00"
    assert frame.data["processor_signature"] == b"\x00\x00\x00"
