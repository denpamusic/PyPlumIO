"""Contains connection representation."""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from collections.abc import Awaitable
import logging
from typing import Any, Dict, Final, Optional, Tuple

from serial import SerialException
import serial_asyncio

from pyplumio.helpers.timeout import timeout
from pyplumio.protocol import Protocol

_LOGGER = logging.getLogger(__name__)

CONNECT_TIMEOUT: Final = 5
RECONNECT_TIMEOUT: Final = 20


class Connection(ABC):
    """Base connection representation. All specific connection classes
    must me inherited from this class."""

    _kwargs: Dict[str, Any]
    _protocol: Optional[Protocol] = None
    _closing: bool = False
    _connection_handler: Awaitable[Any]
    _reconnect_on_failure: bool = True

    def __init__(self, reconnect_on_failure: bool = True, **kwargs):
        """Initialize Connection object."""
        self._kwargs = kwargs
        self._closing = False
        self._protocol = Protocol(
            connection_lost_callback=self._connection_lost_callback
        )
        self._reconnect_on_failure = reconnect_on_failure

    async def __aenter__(self):
        """Provide entry point for context manager."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        """Provide exit point for context manager."""
        await self.close()

    def __getattr__(self, name: str) -> Any:
        """Return attributes from the underlying protocol object."""
        return getattr(self.protocol, name)

    async def _connection_lost_callback(self) -> None:
        """Callback to resume the connection on connection lost."""
        if self._reconnect_on_failure and not self._closing:
            await self._reconnect()

    @timeout(CONNECT_TIMEOUT)
    async def _connect(self) -> None:
        """Establish connection and initialize the protocol object."""
        reader, writer = await self._open_connection()
        self._protocol.connection_established(reader, writer)

    async def _reconnect(self) -> None:
        """Establish connection and reconnect on failure."""
        while True:
            try:
                await self._connect()
                return
            except (
                OSError,
                SerialException,
                asyncio.TimeoutError,
            ):
                _LOGGER.error(
                    "Connection error: connection failed, reconnecting in %i seconds...",
                    RECONNECT_TIMEOUT,
                )
                await asyncio.sleep(RECONNECT_TIMEOUT)

    async def connect(self) -> None:
        """Initialize the connection. This method initializes
        connection via connect or reconnect routines, depending
        on _reconnect_on_failure property."""
        if self._reconnect_on_failure:
            await self._reconnect()
        else:
            await self._connect()

    async def close(self) -> None:
        """Close the connection."""
        self._closing = True
        if self.protocol is not None:
            await self.protocol.shutdown()

    @property
    def protocol(self) -> Optional[Protocol]:
        """Return protocol object."""
        return self._protocol

    @abstractmethod
    async def _open_connection(
        self,
    ) -> Tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Open the connection and return reader and writer objects."""


class TcpConnection(Connection):
    """Represents TCP connection."""

    def __init__(self, host: str, port: int, **kwargs):
        """Initialize TCP connection object."""
        super().__init__(**kwargs)
        self.host = host
        self.port = port

    def __repr__(self):
        """Return string representation of the class."""
        return f"""TcpConnection(
    host = {self.host},
    port = {self.port},
    kwargs = {self._kwargs}
)
"""

    async def _open_connection(
        self,
    ) -> Tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Open the connection and return reader and writer objects."""
        return await asyncio.open_connection(
            host=self.host, port=self.port, **self._kwargs
        )


class SerialConnection(Connection):
    """Represents Serial connection."""

    def __init__(self, device: str, baudrate: int = 115200, **kwargs):
        """Initialize Serial connection object."""
        super().__init__(**kwargs)
        self.device = device
        self.baudrate = baudrate

    def __repr__(self):
        """Return string representation of the class."""
        return f"""SerialConnection(
    device = {self.device},
    baudrate = {self.baudrate},
    kwargs = {self._kwargs}
)
"""

    async def _open_connection(
        self,
    ) -> Tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Open the connection and return reader and writer objects."""
        return await serial_asyncio.open_serial_connection(
            url=self.device,
            baudrate=self.baudrate,
            bytesize=serial_asyncio.serial.EIGHTBITS,
            parity=serial_asyncio.serial.PARITY_NONE,
            stopbits=serial_asyncio.serial.STOPBITS_ONE,
            **self._kwargs,
        )
