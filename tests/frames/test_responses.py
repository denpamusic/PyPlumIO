"""Test PyPlumIO response frames."""

from pyplumio.constants import (
    BROADCAST_ADDRESS,
    DATA_BOILER_PARAMETERS,
    DATA_MIXER_PARAMETERS,
    DATA_MODE,
    DATA_NETWORK,
    DATA_PASSWORD,
    DATA_PRODUCT,
    DATA_SCHEMA,
    DATA_VERSION,
    ECONET_ADDRESS,
)
from pyplumio.data_types import Byte
from pyplumio.frames import responses
from pyplumio.frames.responses import REGDATA_SCHEMA, DataSchema
from pyplumio.helpers.network_info import (
    EthernetParameters,
    NetworkInfo,
    WirelessParameters,
)
from pyplumio.helpers.product_info import ProductInfo
from pyplumio.helpers.version_info import VersionInfo
from pyplumio.structures.boiler_parameters import BOILER_PARAMETERS


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


_program_version_data = {DATA_VERSION: VersionInfo(software="1.0.0")}
_program_version_bytes = bytearray.fromhex("FFFF057A0000000001000000000056")


def test_program_version_create_message() -> None:
    """Test creating program version message."""
    frame = responses.ProgramVersion(
        recipient=BROADCAST_ADDRESS, sender=ECONET_ADDRESS, data=_program_version_data
    )
    assert frame.create_message() == _program_version_bytes


def test_program_version_parse_message() -> None:
    """Test parsing program version message."""
    frame = responses.ProgramVersion(
        recipient=BROADCAST_ADDRESS,
        sender=ECONET_ADDRESS,
        message=_program_version_bytes,
    )
    assert frame.data == _program_version_data


_device_available_data = {
    DATA_NETWORK: NetworkInfo(
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
_device_available_bytes = bytearray.fromhex(
    "01C0A80102FFFFFF00C0A8010101C0A80202FFFFFF00C0A802010101640100000000057465737473"
)


def test_device_available_create_message() -> None:
    """Test creating device available message."""
    frame = responses.DeviceAvailable(
        recipient=BROADCAST_ADDRESS, sender=ECONET_ADDRESS, data=_device_available_data
    )
    assert frame.create_message() == _device_available_bytes


def test_device_available_parse_message() -> None:
    """Test parsing device available message."""
    frame = responses.DeviceAvailable(message=_device_available_bytes)
    assert frame.data == _device_available_data


_uid_data = {
    DATA_PRODUCT: ProductInfo(
        type=0,
        product=90,
        uid="D251PAKR3GCPZ1K8G05G0",
        logo=23040,
        image=2816,
        model="EM350P2-ZF",
    )
}
_uid_bytes = bytearray.fromhex(
    "005A000B001600110D3833383655395A0000000A454D33353050322D5A46"
)


def test_uid_parse_message() -> None:
    """Test parsing UID message."""
    frame = responses.UID(message=_uid_bytes)
    assert frame.data == _uid_data


_password_bytes = bytearray.fromhex("0430303030")
_password_data = {DATA_PASSWORD: "0000"}


def test_password_parse_message() -> None:
    """Test parsing password message."""
    frame = responses.Password(message=_password_bytes)
    assert frame.data == _password_data


_boiler_parameters_bytes = bytearray.fromhex("000005503D643C294C28143BFFFFFF1401FA")
_boiler_parameters_data = {
    BOILER_PARAMETERS[0]: (BOILER_PARAMETERS[0], 80, 61, 100),
    BOILER_PARAMETERS[1]: (BOILER_PARAMETERS[1], 60, 41, 76),
    BOILER_PARAMETERS[2]: (BOILER_PARAMETERS[2], 40, 20, 59),
    BOILER_PARAMETERS[4]: (BOILER_PARAMETERS[4], 20, 1, 250),
}


def test_boiler_parameters_parse_message() -> None:
    """Test parsing boiler parameters message."""
    frame = responses.BoilerParameters(message=_boiler_parameters_bytes)
    assert frame.data == {DATA_BOILER_PARAMETERS: _boiler_parameters_data}


_mixer_parameters_bytes = bytearray.fromhex("000002011E283C141E28")
_mixer_parameters_data = [
    {
        "mix_target_temp": ("mix_target_temp", 30, 40, 60),
        "min_mix_target_temp": ("min_mix_target_temp", 20, 30, 40),
    }
]


def test_mixer_parameters_parse_message() -> None:
    """Test parsing message for mixer parameters response."""
    frame = responses.MixerParameters(message=_mixer_parameters_bytes)
    print(frame.data)
    print({DATA_MIXER_PARAMETERS: _mixer_parameters_data})
    assert frame.data == {DATA_MIXER_PARAMETERS: _mixer_parameters_data}


_data_schema_bytes_empty = bytearray.fromhex("0000")


def test_data_schema_parse_message(data_schema: DataSchema) -> None:
    """Test parsing message for data schema response."""
    assert DATA_SCHEMA in data_schema.data
    assert len(data_schema.data[DATA_SCHEMA]) == 257
    matches = {
        x[0]: x[1]
        for x in data_schema.data[DATA_SCHEMA]
        if x[0] in REGDATA_SCHEMA.values()
    }
    assert list(matches.keys()).sort() == list(REGDATA_SCHEMA.values()).sort()
    assert isinstance(matches[DATA_MODE], Byte)


def test_data_schema_parse_message_with_no_parameters() -> None:
    """Test parsing message for data schema with no parameters."""
    frame = DataSchema(message=_data_schema_bytes_empty)
    assert frame.data == {DATA_SCHEMA: []}
