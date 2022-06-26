"""Fixtures for PyPlumIO test suite."""

import asyncio
from asyncio import StreamReader, StreamWriter
from typing import Generator
from unittest.mock import patch

import pytest

from pyplumio.devices import EcoMAX, EcoSTER
from pyplumio.frames.responses import DataSchema


@pytest.fixture(name="ecomax")
def fixture_ecomax() -> EcoMAX:
    """Return instance of ecoMAX device class."""
    return EcoMAX(queue=asyncio.Queue())


@pytest.fixture(name="ecoster")
def fixture_ecoster() -> EcoSTER:
    """Return instance of ecoSTER device class."""
    return EcoSTER(queue=asyncio.Queue())


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


@pytest.fixture(name="data_schema")
def fixture_data_schema() -> Generator[DataSchema, None, None]:
    """Return sample data schema response from ecoMAX920."""
    data_schema_bytes = bytearray.fromhex(
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
00CC300""".replace(
            "\n", ""
        )
    )

    yield DataSchema(message=data_schema_bytes)
