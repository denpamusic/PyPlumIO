"""Contains a connection class."""
from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from collections.abc import MutableMapping
import logging
from typing import Any, Final

from serial import SerialException
import serial_asyncio

from pyplumio.exceptions import ConnectionFailedError
from pyplumio.helpers.timeout import timeout
from pyplumio.protocol import Protocol

_LOGGER = logging.getLogger(__name__)

CONNECT_TIMEOUT: Final = 5
RECONNECT_TIMEOUT: Final = 20


class Connection(ABC):
    """Represents a connection.

    All specific connection classes MUST be inherited from this class.
    """

    _kwargs: MutableMapping[str, Any]
    _protocol: Protocol
    _closing: bool = False
    _reconnect_on_failure: bool = True

    def __init__(
        self,
        reconnect_on_failure: bool = True,
        ethernet_parameters=None,
        wireless_parameters=None,
        **kwargs,
    ):
        """Initialize a new connection."""
        self._kwargs = kwargs
        self._closing = False
        self._protocol = Protocol(
            self._connection_lost,
            ethernet_parameters,
            wireless_parameters,
        )
        self._reconnect_on_failure = reconnect_on_failure

    async def __aenter__(self):
        """Provide an entry point for the context manager."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        """Provide an exit point for the context manager."""
        await self.close()

    def __getattr__(self, name: str):
        """Return an attributes from the underlying protocol object."""
        return getattr(self.protocol, name)

    async def _connect(self) -> None:
        """Establish connection and initialize the protocol object."""
        try:
            reader, writer = await self._open_connection()
            self._protocol.connection_established(reader, writer)
        except (
            OSError,
            SerialException,
            asyncio.TimeoutError,
        ) as connection_error:
            raise ConnectionFailedError from connection_error

    async def _reconnect(self) -> None:
        """Try to connect and reconnect on failure."""
        try:
            return await self._connect()
        except ConnectionFailedError:
            await self._connection_lost()

    async def _connection_lost(self) -> None:
        """Resume connection on the connection loss."""
        if self._reconnect_on_failure and not self._closing:
            _LOGGER.error(
                "Can't connect to the device, retrying in %.1f seconds",
                RECONNECT_TIMEOUT,
            )
            await asyncio.sleep(RECONNECT_TIMEOUT)
            await self._reconnect()

    async def connect(self) -> None:
        """Open the connection.

        Initializes connection via connect or reconnect
        routines, depending on '_reconnect_on_failure' property."""
        if self._reconnect_on_failure:
            await self._reconnect()
        else:
            await self._connect()

    async def close(self) -> None:
        """Close the connection."""
        self._closing = True
        await self.protocol.shutdown()

    @property
    def protocol(self) -> Protocol:
        """A protocol object."""
        return self._protocol

    @abstractmethod
    async def _open_connection(
        self,
    ) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Open the connection and return reader and writer objects."""


class TcpConnection(Connection):
    """Represents a TCP connection."""

    host: str
    port: int

    def __init__(self, host: str, port: int, **kwargs):
        """Initialize a new TCP connection."""
        super().__init__(**kwargs)
        self.host = host
        self.port = port

    def __repr__(self):
        """Return a string representation of the class."""
        return (
            f"TcpConnection(host={self.host}, port={self.port}, kwargs={self._kwargs})"
        )

    @timeout(CONNECT_TIMEOUT)
    async def _open_connection(
        self,
    ) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Open the connection and return reader and writer objects."""
        return await asyncio.open_connection(
            host=self.host, port=self.port, **self._kwargs
        )


class SerialConnection(Connection):
    """Represents a serial connection."""

    device: str
    baudrate: int

    def __init__(self, device: str, baudrate: int = 115200, **kwargs):
        """Initialize a new serial connection."""
        super().__init__(**kwargs)
        self.device = device
        self.baudrate = baudrate

    def __repr__(self):
        """Return a string representation of the class."""
        return (
            f"SerialConnection(device={self.device}, baudrate={self.baudrate}, "
            + f"kwargs={self._kwargs})"
        )

    @timeout(CONNECT_TIMEOUT)
    async def _open_connection(
        self,
    ) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Open the connection and return reader and writer objects."""
        return await serial_asyncio.open_serial_connection(
            url=self.device,
            baudrate=self.baudrate,
            bytesize=serial_asyncio.serial.EIGHTBITS,
            parity=serial_asyncio.serial.PARITY_NONE,
            stopbits=serial_asyncio.serial.STOPBITS_ONE,
            **self._kwargs,
        )
