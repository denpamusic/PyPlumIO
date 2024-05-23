"""Contains a connection class."""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from collections.abc import MutableMapping
import logging
from typing import Any, Final, cast

from serial import EIGHTBITS, PARITY_NONE, STOPBITS_ONE, SerialException

from pyplumio.exceptions import ConnectionFailedError
from pyplumio.helpers.task_manager import TaskManager
from pyplumio.helpers.timeout import timeout
from pyplumio.protocol import AsyncProtocol, Protocol

_LOGGER = logging.getLogger(__name__)

CONNECT_TIMEOUT: Final = 5
RECONNECT_TIMEOUT: Final = 20

try:
    import serial_asyncio_fast as pyserial_asyncio

    _LOGGER.info("Using pyserial-asyncio-fast in place of pyserial-asyncio")
except ImportError:
    import serial_asyncio as pyserial_asyncio


class Connection(ABC, TaskManager):
    """Represents a connection.

    All specific connection classes MUST be inherited from this class.
    """

    _protocol: Protocol
    _reconnect_on_failure: bool
    _kwargs: MutableMapping[str, Any]

    def __init__(
        self,
        protocol: Protocol | None = None,
        reconnect_on_failure: bool = True,
        **kwargs: Any,
    ) -> None:
        """Initialize a new connection."""
        super().__init__()
        if protocol is None:
            protocol = AsyncProtocol()

        if reconnect_on_failure:
            protocol.on_connection_lost.add(self._reconnect)

        self._reconnect_on_failure = reconnect_on_failure
        self._protocol = protocol
        self._kwargs = kwargs

    async def __aenter__(self) -> Connection:
        """Provide an entry point for the context manager."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        """Provide an exit point for the context manager."""
        await self.close()

    def __getattr__(self, name: str) -> Any:
        """Return an attributes from the underlying protocol object."""
        return getattr(self.protocol, name)

    async def _connect(self) -> None:
        """Establish connection and initialize the protocol object."""
        try:
            reader, writer = cast(
                tuple[asyncio.StreamReader, asyncio.StreamWriter],
                await self._open_connection(),
            )
            self.protocol.connection_established(reader, writer)
        except (OSError, SerialException, asyncio.TimeoutError) as err:
            raise ConnectionFailedError from err

    async def _reconnect(self) -> None:
        """Try to connect and reconnect on failure."""
        try:
            await self._connect()
        except ConnectionFailedError:
            _LOGGER.error(
                "Can't connect to the device, retrying in %.1f seconds",
                RECONNECT_TIMEOUT,
            )
            await asyncio.sleep(RECONNECT_TIMEOUT)
            self.create_task(self._reconnect())

    async def connect(self) -> None:
        """Open the connection.

        Initialize a connection via connect or reconnect
        routines, depending on '_reconnect_on_failure' property.
        """
        await (self._reconnect if self._reconnect_on_failure else self._connect)()

    async def close(self) -> None:
        """Close the connection."""
        self.cancel_tasks()
        await self.protocol.shutdown()

    @property
    def protocol(self) -> Protocol:
        """Return the protocol object."""
        return self._protocol

    @timeout(CONNECT_TIMEOUT)
    @abstractmethod
    async def _open_connection(
        self,
    ) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Open the connection and return reader and writer objects."""


class TcpConnection(Connection):
    """Represents a TCP connection."""

    host: str
    port: int

    def __init__(
        self,
        host: str,
        port: int,
        *,
        protocol: Protocol | None = None,
        reconnect_on_failure: bool = True,
        **kwargs: Any,
    ) -> None:
        """Initialize a new TCP connection."""
        super().__init__(
            protocol,
            reconnect_on_failure,
            **kwargs,
        )
        self.host = host
        self.port = port

    def __repr__(self) -> str:
        """Return a serializable string representation."""
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

    def __init__(
        self,
        device: str,
        baudrate: int = 115200,
        *,
        protocol: Protocol | None = None,
        reconnect_on_failure: bool = True,
        **kwargs: Any,
    ) -> None:
        """Initialize a new serial connection."""
        super().__init__(
            protocol,
            reconnect_on_failure,
            **kwargs,
        )
        self.device = device
        self.baudrate = baudrate

    def __repr__(self) -> str:
        """Return a serializable string representation."""
        return (
            "SerialConnection("
            f"device={self.device}, "
            f"baudrate={self.baudrate}, "
            f"kwargs={self._kwargs})"
        )

    @timeout(CONNECT_TIMEOUT)
    async def _open_connection(
        self,
    ) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Open the connection and return reader and writer objects."""
        return cast(
            tuple[asyncio.StreamReader, asyncio.StreamWriter],
            await pyserial_asyncio.open_serial_connection(
                url=self.device,
                baudrate=self.baudrate,
                bytesize=EIGHTBITS,
                parity=PARITY_NONE,
                stopbits=STOPBITS_ONE,
                **self._kwargs,
            ),
        )
