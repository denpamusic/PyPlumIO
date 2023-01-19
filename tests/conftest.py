"""Fixtures for PyPlumIO test suite."""

import asyncio
from asyncio import StreamReader, StreamWriter
from datetime import datetime
from typing import Dict, Generator, List
from unittest.mock import AsyncMock, patch

import pytest

from pyplumio.const import (
    ATTR_DEVICE_INDEX,
    ATTR_INDEX,
    ATTR_OFFSET,
    ATTR_PARAMETER,
    ATTR_PASSWORD,
    ATTR_SCHEDULE,
    ATTR_SWITCH,
    ATTR_TYPE,
    ATTR_VALUE,
    AlertType,
    FrameType,
)
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.devices.ecoster import EcoSTER
from pyplumio.helpers.network_info import (
    EthernetParameters,
    NetworkInfo,
    WirelessParameters,
)
from pyplumio.helpers.product_info import ConnectedModules, ProductInfo, ProductType
from pyplumio.helpers.typing import DeviceDataType
from pyplumio.helpers.version_info import VersionInfo
from pyplumio.structures.alerts import ATTR_ALERTS, Alert
from pyplumio.structures.ecomax_parameters import ATTR_ECOMAX_PARAMETERS
from pyplumio.structures.mixer_parameters import ATTR_MIXER_PARAMETERS
from pyplumio.structures.network_info import ATTR_NETWORK
from pyplumio.structures.product_info import ATTR_PRODUCT
from pyplumio.structures.program_version import ATTR_VERSION
from pyplumio.structures.schedules import ATTR_SCHEDULE_PARAMETERS, ATTR_SCHEDULES
from pyplumio.structures.thermostat_parameters import (
    ATTR_THERMOSTAT_PARAMETERS,
    ATTR_THERMOSTAT_PROFILE,
)
from pyplumio.structures.thermostat_sensors import ATTR_THERMOSTAT_COUNT

TEST_SCHEDULE: List[bool] = [
    False,
    False,
    False,
    False,
    False,
    False,
    False,
    False,
    False,
    False,
    False,
    False,
    False,
    False,
    False,
    False,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    False,
]


@pytest.fixture(name="data")
def fixture_data() -> Dict[int, DeviceDataType]:
    """Return response data keyed by frame type."""
    return {
        FrameType.RESPONSE_PROGRAM_VERSION: {
            ATTR_VERSION: VersionInfo(software="1.0.0")
        },
        FrameType.RESPONSE_DEVICE_AVAILABLE: {
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
        FrameType.RESPONSE_UID: {
            ATTR_PRODUCT: ProductInfo(
                type=ProductType.ECOMAX_P,
                product=90,
                uid="D251PAKR3GCPZ1K8G05G0",
                logo=23040,
                image=2816,
                model="EM350P2-ZF",
            )
        },
        FrameType.RESPONSE_PASSWORD: {ATTR_PASSWORD: "0000"},
        FrameType.RESPONSE_ECOMAX_PARAMETERS: {
            ATTR_ECOMAX_PARAMETERS: [
                (0, (61, 61, 100)),
                (1, (60, 41, 60)),
                (2, (40, 20, 59)),
                (14, (20, 1, 250)),
                (15, (3, 1, 30)),
                (16, (1, 1, 30)),
                (17, (5, 1, 30)),
                (18, (1, 0, 1)),
                (19, (0, 0, 60)),
                (20, (60, 0, 100)),
                (23, (20, 10, 100)),
                (35, (30, 20, 100)),
                (36, (4, 1, 30)),
                (37, (0, 0, 100)),
                (38, (8, 1, 250)),
                (39, (50, 40, 85)),
                (40, (10, 10, 30)),
                (41, (30, 20, 50)),
                (44, (10, 10, 240)),
                (47, (15, 10, 20)),
                (50, (50, 40, 150)),
                (53, (2, 1, 15)),
                (54, (3, 1, 10)),
                (55, (40, 20, 60)),
                (60, (60, 1, 250)),
                (61, (30, 20, 50)),
                (85, (125, 1, 250)),
                (87, (2, 1, 100)),
                (88, (47, 1, 250)),
                (89, (10, 10, 30)),
                (98, (65, 50, 80)),
                (99, (50, 30, 80)),
                (100, (80, 60, 90)),
                (101, (50, 30, 80)),
                (102, (0, 0, 99)),
                (105, (5, 3, 15)),
                (106, (0, 0, 1)),
                (107, (13, 1, 40)),
                (108, (20, 0, 40)),
                (111, (0, 0, 1)),
                (112, (5, 0, 30)),
                (114, (90, 85, 95)),
                (115, (60, 40, 90)),
                (119, (51, 40, 70)),
                (120, (40, 20, 55)),
                (121, (70, 40, 80)),
                (122, (2, 0, 2)),
                (123, (10, 1, 30)),
                (124, (0, 0, 1)),
                (125, (0, 0, 2)),
                (126, (16, 5, 30)),
                (127, (10, 1, 15)),
                (128, (3, 0, 99)),
            ]
        },
        FrameType.RESPONSE_MIXER_PARAMETERS: {
            ATTR_MIXER_PARAMETERS: [
                (
                    0,
                    [
                        (0, (40, 30, 60)),
                        (1, (20, 30, 40)),
                        (2, (80, 70, 90)),
                        (3, (20, 10, 30)),
                        (4, (1, 0, 1)),
                        (5, (13, 10, 30)),
                    ],
                )
            ]
        },
        FrameType.RESPONSE_THERMOSTAT_PARAMETERS: {
            ATTR_THERMOSTAT_COUNT: 3,
            ATTR_THERMOSTAT_PROFILE: (0, 0, 5),
            ATTR_THERMOSTAT_PARAMETERS: [
                (
                    0,
                    [
                        (0, (0, 0, 7)),
                        (1, (220, 100, 350)),
                        (2, (150, 100, 350)),
                        (3, (100, 60, 140)),
                        (4, (2, 0, 60)),
                        (5, (1, 0, 60)),
                        (6, (1, 0, 60)),
                        (7, (10, 0, 60)),
                        (8, (9, 0, 50)),
                        (9, (222, 100, 350)),
                        (10, (212, 100, 350)),
                        (11, (90, 50, 300)),
                    ],
                )
            ],
        },
        FrameType.RESPONSE_ALERTS: {
            ATTR_ALERTS: [
                Alert(
                    code=26,
                    from_dt=datetime(2022, 7, 23, 16, 27),
                    to_dt=datetime(2022, 7, 23, 16, 32, 27),
                ),
                Alert(
                    code=AlertType.POWER_LOSS,
                    from_dt=datetime(2022, 7, 22, 22, 33),
                    to_dt=datetime(2022, 7, 22, 22, 38, 11),
                ),
            ]
        },
        FrameType.RESPONSE_SCHEDULES: {
            ATTR_SCHEDULES: [(0, [TEST_SCHEDULE] * 7)],
            ATTR_SCHEDULE_PARAMETERS: [(0, (0, 0, 1)), (1, (5, 0, 30))],
        },
        FrameType.REQUEST_SET_ECOMAX_PARAMETER: {
            ATTR_INDEX: 0,
            ATTR_VALUE: 80,
        },
        FrameType.REQUEST_SET_MIXER_PARAMETER: {
            ATTR_INDEX: 0,
            ATTR_VALUE: 40,
            ATTR_DEVICE_INDEX: 0,
        },
        FrameType.REQUEST_SET_THERMOSTAT_PARAMETER: {
            ATTR_INDEX: 1,
            ATTR_VALUE: 42,
            ATTR_OFFSET: 12,
        },
        FrameType.REQUEST_ECOMAX_CONTROL: {ATTR_VALUE: 1},
        FrameType.REQUEST_SET_SCHEDULE: {
            ATTR_TYPE: "heating",
            ATTR_SWITCH: 0,
            ATTR_PARAMETER: 5,
            ATTR_SCHEDULE: [TEST_SCHEDULE] * 7,
        },
        FrameType.MESSAGE_SENSOR_DATA: {
            "sensors": {
                "frame_versions": {
                    85: 45559,
                    84: 48672,
                    86: 64152,
                    54: 1,
                    56: 2,
                    57: 1,
                    61: 12568,
                },
                "state": 0,
                "fan": False,
                "feeder": False,
                "heating_pump": False,
                "water_heater_pump": False,
                "ciculation_pump": False,
                "lighter": False,
                "alarm": False,
                "outer_boiler": False,
                "fan2_exhaust": False,
                "feeder2": False,
                "outer_feeder": False,
                "solar_pump": False,
                "fireplace_pump": False,
                "gcz_contact": False,
                "blow_fan1": False,
                "blow_fan2": False,
                "heating_pump_flag": True,
                "water_heater_pump_flag": True,
                "circulation_pump_flag": True,
                "solar_pump_flag": False,
                "heating_temp": 22.384185791015625,
                "optical_temp": 0.0,
                "heating_target": 41,
                "heating_status": 0,
                "water_heater_target": 45,
                "water_heater_status": 128,
                "pending_alerts": 0,
                "fuel_level": 32,
                "transmission": 0,
                "fan_power": 0.0,
                "load": 0,
                "power": 0.0,
                "fuel_consumption": 0.0,
                "thermostat": 1,
                "modules": ConnectedModules(
                    module_a="18.11.58.K1",
                    module_b=None,
                    module_c=None,
                    module_lambda=None,
                    module_ecoster=None,
                    module_panel="18.10.72",
                ),
                "lambda_sensor": {"state": 1, "target": 2, "level": 40},
                "thermostat_sensors": [
                    (
                        0,
                        {
                            "state": 3,
                            "current_temp": 43.5,
                            "target_temp": 50.0,
                            "contacts": True,
                            "schedule": False,
                        },
                    )
                ],
                "thermostat_count": 1,
                "mixer_sensors": [
                    (4, {"current_temp": 20.0, "target_temp": 40, "pump": False})
                ],
                "mixer_count": 5,
            }
        },
    }


@pytest.fixture(name="messages")
def fixture_messages() -> Dict[int, bytearray]:
    """Return response messages keyed by frame type."""
    return {
        FrameType.RESPONSE_PROGRAM_VERSION: bytearray.fromhex(
            "FFFF057A0000000001000000000056"
        ),
        FrameType.RESPONSE_DEVICE_AVAILABLE: bytearray.fromhex(
            """01C0A80102FFFFFF00C0A8010101C0A80202FFFFFF00C0A80201010164010000000005746
5737473""".replace(
                "\n", ""
            )
        ),
        FrameType.RESPONSE_UID: bytearray.fromhex(
            "005A000B001600110D3833383655395A0000000A454D33353050322D5A46"
        ),
        FrameType.RESPONSE_PASSWORD: bytearray.fromhex("0430303030"),
        FrameType.RESPONSE_ECOMAX_PARAMETERS: bytearray.fromhex(
            """00008b3d3d643c293c28143bfffffffffffffffffffffffffffffffffffffffffffffffff
fffffffffffffffff1401fa03011e01011e05011e01000100003c3c0064ffffffffffff140a64fffffffffff
fffffffffffffffffffffffffffffffffffffffffffffffffffffff1e146404011e0000640801fa3228550a0
a1e1e1432ffffffffffff0a0af0ffffffffffff0f0a14ffffffffffff322896ffffffffffff02010f03010a2
8143cffffffffffffffffffffffff3c01fa1e1432fffffffffffffffffffffffffffffffffffffffffffffff
ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff
fff7d01faffffff0201642f01fa0a0a1effffffffffffffffffffffffffffffffffffffffffffffff4132503
21e50503c5a321e50000063ffffffffffff05030f0000010d0128140028ffffffffffff00000105001efffff
f5a555f3c285affffffffffffffffff3328462814374628500200020a011e00000100000210051e0a010f030
063ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff""".replace(
                "\n", ""
            )
        ),
        FrameType.RESPONSE_MIXER_PARAMETERS: bytearray.fromhex(
            "00000601281E3C141E2850465A140A1E0100010D0A1E"
        ),
        FrameType.RESPONSE_THERMOSTAT_PARAMETERS: bytearray.fromhex(
            """000025000005000007DC0064005E01960064005E01643C8C02003C01003C01003C0A003C0
90032DE0064005E01D40064005E015A0032002C01FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF""".replace(
                "\n", ""
            )
        ),
        FrameType.RESPONSE_DATA_SCHEMA: bytearray.fromhex(
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
        FrameType.RESPONSE_ALERTS: bytearray.fromhex(
            "6400021a5493382B9B94382B009C97372BD398372B"
        ),
        FrameType.RESPONSE_SCHEDULES: bytearray.fromhex(
            """100101000005001E0000FFFFFFFE0000FFFFFFFE0000FFFFFFFE0000FFFFFFFE0000FFFFF
FFE0000FFFFFFFE0000FFFFFFFE
""".replace(
                "\n", ""
            )
        ),
        FrameType.MESSAGE_REGULATOR_DATA: bytearray.fromhex(
            """626400010855F7B15420BE6101003D183136010064010040041C5698FA0000000000FF0FF
F0FFF0FFF0FFF0FFF0F9F04080FFF0FFF0F0000000000000000000000000000000000000000000000000000C
07F0000C07F0000C07F0000C07F0000C07F0000C07FD012B341000000000000C07F0000C07F0000C07F0000C
07F0000C07F0000C07F0000C07F0000C07F0000C07F0000C07F0000C07F0000C07F0000C07F0000C07F2D280
000000029000000002828000000002828000000800000000000000000000000000000000000000000003FFF7
F00000000200000000000404000403F124B01000000000000000000000002020100000000000000000000000
000000000000000000000150009001A000D000C001D00000000000000000000000000000000000000FFFFFF0
0000000000000000000FFFFFF0000000000010164000000
""".replace(
                "\n", ""
            )
        ),
        FrameType.MESSAGE_SENSOR_DATA: bytearray.fromhex(
            """0755F7B15420BE5698FA3601003802003901003D18310000000000FF0300000900D012B34
101FFFFFFFF02FFFFFFFF03FFFFFFFF04FFFFFFFF05FFFFFFFF060000000007FFFFFFFF08FFFFFFFF29002D8
00020000000000000000000000000000001120B3A4B01FFFFFFFF120A480102280005010300002E420000484
205FFFFFFFF28000800FFFFFFFF28000800FFFFFFFF28000800FFFFFFFF280008000000A04128000800
""".replace(
                "\n", ""
            )
        ),
        FrameType.REQUEST_ECOMAX_PARAMETERS: bytearray.fromhex("FF00"),
        FrameType.REQUEST_SET_ECOMAX_PARAMETER: bytearray.fromhex("0050"),
        FrameType.REQUEST_SET_MIXER_PARAMETER: bytearray.fromhex("000028"),
        FrameType.REQUEST_SET_THERMOSTAT_PARAMETER: bytearray.fromhex("0d2a"),
        FrameType.REQUEST_ECOMAX_CONTROL: bytearray.fromhex("01"),
        FrameType.REQUEST_SET_SCHEDULE: bytearray.fromhex(
            """010000050000FFFFFFFE0000FFFFFFFE0000FFFFFFFE0000FFFFFFFE0000FFFFFFFE0000F
FFFFFFE0000FFFFFFFE
""".replace(
                "\n", ""
            )
        ),
    }


@pytest.fixture(name="sensor_data_without_thermostats")
def fixture_sensor_data_without_thermostats() -> bytearray:
    """Return device sensor data without thermostat data."""
    return bytearray.fromhex(
        """0755F7B15420BE5698FA3601003802003901003D18310000000000FF0300000900D012B34101F
FFFFFFF02FFFFFFFF03FFFFFFFF04FFFFFFFF05FFFFFFFF060000000007FFFFFFFF08FFFFFFFF29002D80002
0000000000000000000000000000001120B3A4B01FFFFFFFF120A4801022800FF05FFFFFFFF28000800FFFFF
FFF28000800FFFFFFFF28000800FFFFFFFF28000800FFFFFFFF28000800
    """.replace(
            "\n", ""
        )
    )


@pytest.fixture(name="ecomax")
def fixture_ecomax() -> EcoMAX:
    """Return instance of ecomax."""
    with patch("pyplumio.devices.ecomax.EcoMAX.subscribe_once"):
        ecomax = EcoMAX(asyncio.Queue())

    ecomax.data[ATTR_PRODUCT] = ProductInfo(
        type=ProductType.ECOMAX_P,
        product=90,
        uid="D251PAKR3GCPZ1K8G05G0",
        logo=23040,
        image=2816,
        model="EM350P2-ZF",
    )
    return ecomax


@pytest.fixture(name="ecoster")
def fixture_ecoster() -> EcoSTER:
    """Return instance of ecoster."""
    return EcoSTER(asyncio.Queue())


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
