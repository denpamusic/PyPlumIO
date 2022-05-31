"""Test PyPlumIO response frames."""

from pyplumio import responses
from pyplumio.constants import (
    BROADCAST_ADDRESS,
    ECONET_ADDRESS,
    WLAN_ENCRYPTION,
    WLAN_ENCRYPTION_NONE,
)

_program_version_data = {
    "version": "1.0.0",
    "struct_tag": b"\xFF\xFF",
    "struct_version": 5,
    "device_id": b"\x7A\x00",
    "processor_signature": b"\x00\x00\x00",
    "address": 0x56,
}

_program_version_bytes = bytearray(
    b"\xFF\xFF\x05\x7A\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x56"
)

_device_available_data = {
    "eth": {
        "ip": "192.168.1.2",
        "netmask": "255.255.255.0",
        "gateway": "192.168.1.1",
        "status": True,
    },
    "wlan": {
        "ip": "192.168.2.2",
        "netmask": "255.255.255.0",
        "gateway": "192.168.2.1",
        "encryption": WLAN_ENCRYPTION[WLAN_ENCRYPTION_NONE],
        "quality": 100,
        "status": True,
        "ssid": "tests",
    },
    "server": {"status": True},
}

_device_available_bytes = bytearray(
    b"\x01\xC0\xA8\x01\x02\xFF\xFF\xFF\x00\xC0\xA8\x01\x01\x01"
    + b"\xC0\xA8\x02\x02\xFF\xFF\xFF\x00\xC0\xA8\x02\x01\x01\x01\x64\x01\x00\x00"
    + b"\x00\x00\x05\x74\x65\x73\x74\x73"
)


def test_responses_type() -> None:
    """Test if response is instance of frame class."""
    for response in (
        responses.ProgramVersion,
        responses.DeviceAvailable,
        responses.RegData,
        responses.CurrentData,
        responses.UID,
        responses.Password,
        responses.BoilerParameters,
        responses.MixerParameters,
        responses.DataSchema,
    ):
        frame = response(recipient=BROADCAST_ADDRESS, sender=ECONET_ADDRESS)
        assert isinstance(frame, response)


def test_program_version_create_message() -> None:
    """Test creating message for program version response."""
    frame = responses.ProgramVersion(
        recipient=BROADCAST_ADDRESS, sender=ECONET_ADDRESS, data=_program_version_data
    )
    assert frame.create_message() == _program_version_bytes


def test_program_version_parse_message() -> None:
    """Test parsing message for program version response."""
    frame = responses.ProgramVersion(recipient=BROADCAST_ADDRESS, sender=ECONET_ADDRESS)
    frame.parse_message(_program_version_bytes)
    assert frame.data == _program_version_data


def test_device_available_create_message() -> None:
    """Test creating message for device available response."""
    frame = responses.DeviceAvailable(
        recipient=BROADCAST_ADDRESS, sender=ECONET_ADDRESS, data=_device_available_data
    )
    assert frame.create_message() == _device_available_bytes


def test_device_available_parse_message() -> None:
    """Test parsing message for device available response."""
    frame = responses.DeviceAvailable(
        recipient=BROADCAST_ADDRESS, sender=ECONET_ADDRESS
    )
    frame.parse_message(_device_available_bytes)
    print(frame.data)
    assert frame.data == _device_available_data
