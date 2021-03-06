"""Fixtures for PyPlumIO test suite."""

from asyncio import StreamReader, StreamWriter
from datetime import datetime
from typing import Dict, Generator
from unittest.mock import AsyncMock, patch

import pytest

from pyplumio.const import (
    ATTR_ALERTS,
    ATTR_BOILER_PARAMETERS,
    ATTR_EXTRA,
    ATTR_MIXER_PARAMETERS,
    ATTR_NAME,
    ATTR_NETWORK,
    ATTR_PASSWORD,
    ATTR_PRODUCT,
    ATTR_VALUE,
    ATTR_VERSION,
)
from pyplumio.frames import MessageTypes, RequestTypes, ResponseTypes
from pyplumio.helpers.network_info import (
    EthernetParameters,
    NetworkInfo,
    WirelessParameters,
)
from pyplumio.helpers.product_info import ProductInfo
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.helpers.version_info import VersionInfo
from pyplumio.structures.alerts import Alert
from pyplumio.structures.boiler_parameters import BOILER_PARAMETERS


@pytest.fixture(name="data")
def fixture_data() -> Dict[int, DeviceDataType]:
    """Return response data keyed by frame type."""
    return {
        ResponseTypes.PROGRAM_VERSION: {ATTR_VERSION: VersionInfo(software="1.0.0")},
        ResponseTypes.DEVICE_AVAILABLE: {
            ATTR_NETWORK: NetworkInfo(
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
        },
        ResponseTypes.UID: {
            ATTR_PRODUCT: ProductInfo(
                type=0,
                product=90,
                uid="D251PAKR3GCPZ1K8G05G0",
                logo=23040,
                image=2816,
                model="EM350P2-ZF",
            )
        },
        ResponseTypes.PASSWORD: {ATTR_PASSWORD: "0000"},
        ResponseTypes.BOILER_PARAMETERS: {
            ATTR_BOILER_PARAMETERS: {
                BOILER_PARAMETERS[0]: (80, 61, 100),
                BOILER_PARAMETERS[1]: (60, 41, 76),
                BOILER_PARAMETERS[2]: (40, 20, 59),
                BOILER_PARAMETERS[4]: (20, 1, 250),
            }
        },
        ResponseTypes.MIXER_PARAMETERS: {
            ATTR_MIXER_PARAMETERS: [
                {
                    "mix_target_temp": (30, 40, 60),
                    "min_mix_target_temp": (20, 30, 40),
                }
            ]
        },
        ResponseTypes.ALERTS: {
            ATTR_ALERTS: [
                Alert(
                    code=0,
                    from_dt=datetime(2022, 7, 23, 16, 27),
                    to_dt=datetime(2022, 7, 23, 16, 32, 27),
                ),
                Alert(
                    code=0,
                    from_dt=datetime(2022, 7, 22, 22, 33),
                    to_dt=datetime(2022, 7, 22, 22, 38, 11),
                ),
            ]
        },
        RequestTypes.SET_BOILER_PARAMETER: {
            ATTR_NAME: "airflow_power_100",
            ATTR_VALUE: 80,
        },
        RequestTypes.SET_MIXER_PARAMETER: {
            ATTR_NAME: "mix_target_temp",
            ATTR_VALUE: 40,
            ATTR_EXTRA: 0,
        },
        RequestTypes.BOILER_CONTROL: {ATTR_VALUE: 1},
    }


@pytest.fixture(name="messages")
def fixture_messages() -> Dict[int, bytearray]:
    """Return response messages keyed by frame type."""
    return {
        ResponseTypes.PROGRAM_VERSION: bytearray.fromhex(
            "FFFF057A0000000001000000000056"
        ),
        ResponseTypes.DEVICE_AVAILABLE: bytearray.fromhex(
            "01C0A80102FFFFFF00C0A8010101C0A80202FFFFFF00C0A802010101640100000000057465737473"
        ),
        ResponseTypes.UID: bytearray.fromhex(
            "005A000B001600110D3833383655395A0000000A454D33353050322D5A46"
        ),
        ResponseTypes.PASSWORD: bytearray.fromhex("0430303030"),
        ResponseTypes.BOILER_PARAMETERS: bytearray.fromhex(
            "000005503D643C294C28143BFFFFFF1401FA"
        ),
        ResponseTypes.MIXER_PARAMETERS: bytearray.fromhex("000002011E283C141E28"),
        ResponseTypes.DATA_SCHEMA: bytearray.fromhex(
            """01010400070A02060A00060A01060A02000A01000A0
3060A07060A05060A06060A08060A09060A0A060A03000A04060A0B060A0C060A0D060A0E060A0F060A10060
A04000A11060A11060A12060A13060A14060A15060A16060A0500050800050B00050C00050D00050E00050A0
0050900050700050F00051200050600051000051100050600050600051400051500051600051700051800051
900051A00070104070704070304071C00070604070204070004071B000704040705040706000709040708040
70600070600071E00071F00070B04070A0407200007210007220004010504070504030504240004060504020
5040005042300040405040505040600040905040805040600040600042600042700040B05040A05042800042
900042A00042C00042F00043000043100043200042E00042D00042B000433000436000406000434000435000
40600040600043800043900043A00043B00043C00043D00043E000A40000A43000A44000A45000A46000A420
00A41000A3F000A47000A53000A53000A48000A49000A4A000A53000A4C000A4D000A4E000A4F000A50000A5
1000A52000A53000A53000A53000A53000A53000A53000A53000A53000A55000A56000A57000A58000A59000
A5A000A5B000A5C000A5D000A5E000A5F000A5F000A5F000A5F000A5F000A5F000461000462000400080A630
00A64000401080A66000A67000A68000A69000A6A000A6B000A6C000A6D000A6E000A6F000A70000A71000A7
2000A72000A72000A72000473000474000402070A75000A76000A06070A77000A53000A78000A79000A53000
A7A000A7B000A7C000A7D000A7E000A7F0004800004830004840004910004920004930004940004950004960
0049700049800049900049A000A9B000A9C000A9D000A9E000A9F0004A40004A50004A60004A00004A10007A
20007A30004030704600007010707650004AA0004AD0005B00005B10005B20005B30005B50005B60007AB000
5AC0006AE0006AF000FB7000FB8000FB90004BA000FBB000FBC000FBD0004BE0004BF0004C00004C10004C20
00CC300
        """.replace(
                "\n", ""
            )
        ),
        ResponseTypes.ALERTS: bytearray.fromhex(
            "640002005493382B9B94382B009C97372BD398372B"
        ),
        MessageTypes.REGULATOR_DATA: bytearray.fromhex(
            """626400010855F7B15420BE6101003D183136010064010040041C5698FA0000000000FF0FFF0FFF0FF
F0FFF0FFF0F9F04080FFF0FFF0F0000000000000000000000000000000000000000000000000000C07F0000C
07F0000C07F0000C07F0000C07F0000C07FD012B341000000000000C07F0000C07F0000C07F0000C07F0000C
07F0000C07F0000C07F0000C07F0000C07F0000C07F0000C07F0000C07F0000C07F0000C07F2D28000000002
9000000002828000000002828000000800000000000000000000000000000000000000000003FFF7F0000000
0200000000000404000403F124B0100000000000000000000000202010000000000000000000000000000000
0000000000000150009001A000D000C001D00000000000000000000000000000000000000FFFFFF000000000
00000000000FFFFFF0000000000010164000000
""".replace(
                "\n", ""
            )
        ),
        MessageTypes.SENSOR_DATA: bytearray.fromhex(
            """0755F7B15420BE5698FA3601003802003901003D18310000000000FF0300000900D012B34101FFFFF
FFF02FFFFFFFF03FFFFFFFF04FFFFFFFF05FFFFFFFF060000000007FFFFFFFF08FFFFFFFF29002D800020000
000000000000000000000000001120B3A4B01FFFFFFFF120A48FFFF05FFFFFFFF28000800FFFFFFFF2800080
0FFFFFFFF28000800FFFFFFFF28000800FFFFFFFF28000800
""".replace(
                "\n", ""
            )
        ),
        RequestTypes.BOILER_PARAMETERS: bytearray.fromhex("FF00"),
        RequestTypes.SET_BOILER_PARAMETER: bytearray.fromhex("0050"),
        RequestTypes.SET_MIXER_PARAMETER: bytearray.fromhex("000028"),
        RequestTypes.BOILER_CONTROL: bytearray.fromhex("01"),
    }


@pytest.fixture(name="bypass_asyncio_sleep")
def fixture_bypass_asyncio_sleep():
    """Bypass asyncio sleep."""
    with patch("asyncio.sleep"):
        yield


@pytest.fixture(name="bypass_asyncio_create_task")
def fixture_bypass_asyncio_create_task():
    """Bypass asyncio create task."""
    with patch("asyncio.create_task"):
        yield


@pytest.fixture(name="bypass_asyncio_events")
def fixture_bypass_asyncio_events():
    """Do not wait for asyncio events."""
    with patch("asyncio.Event.wait", new_callable=AsyncMock), patch(
        "asyncio.Event.is_set", return_value=True
    ):
        yield


@pytest.fixture(name="stream_writer")
def fixture_stream_writer() -> Generator[StreamWriter, None, None]:
    """Return mock of asyncio stream writer."""
    with patch("asyncio.StreamWriter", autospec=True) as stream_writer:
        yield stream_writer


@pytest.fixture(name="stream_reader")
def fixture_stream_reader() -> Generator[StreamReader, None, None]:
    """Return mock of asyncio stream reader."""
    with patch("asyncio.StreamReader", autospec=True) as stream_reader:
        yield stream_reader


@pytest.fixture(name="open_tcp_connection")
def fixture_open_tcp_connection(
    stream_reader: StreamReader, stream_writer: StreamWriter
) -> Generator:
    """Bypass opening asyncio connection."""
    with patch(
        "asyncio.open_connection", return_value=(stream_reader, stream_writer)
    ) as connection:
        yield connection


@pytest.fixture(name="open_serial_connection")
def fixture_open_serial_connection(
    stream_reader: StreamReader, stream_writer: StreamWriter
) -> Generator:
    """Bypass opening serial_asyncio connection."""
    with patch(
        "serial_asyncio.open_serial_connection",
        return_value=(stream_reader, stream_writer),
    ) as connection:
        yield connection
