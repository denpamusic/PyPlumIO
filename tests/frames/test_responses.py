"""Test PyPlumIO response frames."""

from pyplumio.constants import BROADCAST_ADDRESS, ECONET_ADDRESS
from pyplumio.data_types import Byte
from pyplumio.frames import responses
from pyplumio.helpers.network_info import (
    EthernetParameters,
    NetworkInfo,
    WirelessParameters,
)
from pyplumio.helpers.product_info import ProductInfo
from pyplumio.helpers.version_info import VersionInfo


def test_responses_type() -> None:
    """Test if response is instance of frame class."""
    for response in (
        responses.ProgramVersion,
        responses.DeviceAvailable,
        responses.UID,
        responses.Password,
        responses.BoilerParameters,
        responses.MixerParameters,
        responses.DataSchema,
    ):
        frame = response(recipient=BROADCAST_ADDRESS, sender=ECONET_ADDRESS)
        assert isinstance(frame, response)


_program_version_data = {"version": VersionInfo(software="1.0.0")}
_program_version_bytes = bytearray(
    b"\xFF\xFF\x05\x7A\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x56"
)


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


_device_available_data = {
    "network": NetworkInfo(
        eth=EthernetParameters(
            ip="192.168.1.2",
            netmask="255.255.255.0",
            gateway="192.168.1.1",
            status=True,
        ),
        wlan=WirelessParameters(
            ip="192.168.2.2",
            netmask="255.255.255.0",
            gateway="192.168.2.1",
            status=True,
            ssid="tests",
        ),
    )
}
_device_available_bytes = bytearray(
    b"\x01\xC0\xA8\x01\x02\xFF\xFF\xFF\x00\xC0\xA8\x01\x01\x01"
    + b"\xC0\xA8\x02\x02\xFF\xFF\xFF\x00\xC0\xA8\x02\x01\x01\x01\x64\x01\x00\x00"
    + b"\x00\x00\x05\x74\x65\x73\x74\x73"
)


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
    assert frame.data == _device_available_data


_uid_data = {
    "product": ProductInfo(
        type=0,
        product=90,
        uid="D251PAKR3GCPZ1K8G05G0",
        logo=23040,
        image=2816,
        model="EM350P2-ZF",
    )
}
_uid_bytes = bytearray(
    b"\x00Z\x00\x0b\x00\x16\x00\x11\r8386U9Z\x00\x00\x00\nEM350P2-ZF"
)


def test_uid_parse_message() -> None:
    """Test parsing message for uid response."""
    frame = responses.UID(recipient=BROADCAST_ADDRESS, sender=ECONET_ADDRESS)
    frame.parse_message(_uid_bytes)
    assert frame.data == _uid_data


_password_data = {"password": "0000"}
_password_bytes = bytearray(b"\x040000")


def test_password_parse_message() -> None:
    """Test parsing message for password response."""
    frame = responses.Password(recipient=BROADCAST_ADDRESS, sender=ECONET_ADDRESS)
    frame.parse_message(_password_bytes)
    assert frame.data == _password_data


_data_schema_bytes = bytearray(b"\x01\x00\x04\x00\x07")
_data_schema_bytes_empty = bytearray(b"\x00\x00")
_data_schema_data = {"schema": [("mode", Byte())]}


def test_data_schema_parse_message() -> None:
    """Test parsing message for data schema response."""
    frame = responses.DataSchema(recipient=BROADCAST_ADDRESS, sender=ECONET_ADDRESS)
    frame.parse_message(_data_schema_bytes)
    assert frame.data == _data_schema_data


def test_data_schema_parse_message_with_no_parameters() -> None:
    """Test parsing message for data schema with no parameters."""
    frame = responses.DataSchema(recipient=BROADCAST_ADDRESS, sender=ECONET_ADDRESS)
    frame.parse_message(_data_schema_bytes_empty)
    assert frame.data == {"schema": []}
