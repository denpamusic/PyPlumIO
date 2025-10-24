"""Contains a connection class."""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import logging
from typing import Any, Final

from serial import EIGHTBITS, PARITY_NONE, STOPBITS_ONE

from pyplumio.devices import PhysicalDevice
from pyplumio.exceptions import ConnectionFailedError
from pyplumio.helpers.task_manager import TaskManager
from pyplumio.protocol import AsyncProtocol, Protocol
from pyplumio.utils import timeout

_LOGGER = logging.getLogger(__name__)

TRY_CONNECT_FOR_SECONDS: Final = 5
RECONNECT_AFTER_SECONDS: Final = 20

try:
    import serial_asyncio_fast as pyserial_asyncio

    _LOGGER.info("Using pyserial-asyncio-fast in place of pyserial-asyncio")
except ImportError:
    import serial_asyncio as pyserial_asyncio  # type: ignore[no-redef]


class Connection(ABC, TaskManager):
    """Represents a connection.

    All specific connection classes MUST be inherited from this class.
    """

    __slots__ = ("_protocol", "_reconnect_on_failure", "_options")

    _protocol: Protocol
    _reconnect_on_failure: bool
    _options: dict[str, Any]

    def __init__(
        self,
        protocol: Protocol | None = None,
        reconnect_on_failure: bool = True,
        **options: Any,
    ) -> None:
        """Initialize a new connection."""
        super().__init__()
        if protocol is None:
            protocol = AsyncProtocol()

        if reconnect_on_failure:
            protocol.on_connection_lost.add(self._reconnect)

        self._reconnect_on_failure = reconnect_on_failure
        self._protocol = protocol
        self._options = options

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
            reader, writer = await self._open_connection()
            self.protocol.connection_established(reader, writer)
        except (OSError, asyncio.TimeoutError) as err:
            raise ConnectionFailedError from err

    async def _reconnect(self) -> None:
        """Try to connect and reconnect on failure."""
        try:
            await self._connect()
        except ConnectionFailedError:
            _LOGGER.error(
                "Can't connect to the device, retrying in %.1f seconds",
                RECONNECT_AFTER_SECONDS,
            )
            await asyncio.sleep(RECONNECT_AFTER_SECONDS)
            self.create_task(self._reconnect(), name="reconnect_task")

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

    @asynccontextmanager
    async def device(
        self, name: str, timeout: float | None = None
    ) -> AsyncGenerator[PhysicalDevice]:
        """Get the device in context manager."""
        if not isinstance(self.protocol, AsyncProtocol):
            raise NotImplementedError

        yield await self.protocol.get(name, timeout=timeout)

    @property
    def protocol(self) -> Protocol:
        """Return the protocol object."""
        return self._protocol

    @property
    def options(self) -> dict[str, Any]:
        """Return connection options."""
        return self._options

    @timeout(TRY_CONNECT_FOR_SECONDS)
    @abstractmethod
    async def _open_connection(
        self,
    ) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Open the connection and return reader and writer objects."""


class TcpConnection(Connection):
    """Represents a TCP connection."""

    __slots__ = ("host", "port")

    host: str
    port: int

    def __init__(
        self,
        host: str,
        port: int,
        *,
        protocol: Protocol | None = None,
        reconnect_on_failure: bool = True,
        **options: Any,
    ) -> None:
        """Initialize a new TCP connection."""
        super().__init__(protocol, reconnect_on_failure, **options)
        self.host = host
        self.port = port

    def __repr__(self) -> str:
        """Return a serializable string representation."""
        return (
            f"TcpConnection(host={self.host}, port={self.port}, options={self.options})"
        )

    @timeout(TRY_CONNECT_FOR_SECONDS)
    async def _open_connection(
        self,
    ) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Open the connection and return reader and writer objects."""
        return await asyncio.open_connection(
            host=self.host, port=self.port, **self.options
        )


class SerialConnection(Connection):
    """Represents a serial connection."""

    __slots__ = ("url", "baudrate")

    url: str
    baudrate: int

    def __init__(
        self,
        url: str,
        baudrate: int = 115200,
        *,
        protocol: Protocol | None = None,
        reconnect_on_failure: bool = True,
        **options: Any,
    ) -> None:
        """Initialize a new serial connection."""
        super().__init__(protocol, reconnect_on_failure, **options)
        self.url = url
        self.baudrate = baudrate

    def __repr__(self) -> str:
        """Return a serializable string representation."""
        return (
            "SerialConnection("
            f"url={self.url}, "
            f"baudrate={self.baudrate}, "
            f"options={self.options})"
        )

    @timeout(TRY_CONNECT_FOR_SECONDS)
    async def _open_connection(
        self,
    ) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Open the connection and return reader and writer objects."""
        return await pyserial_asyncio.open_serial_connection(
            url=self.url,
            baudrate=self.baudrate,
            bytesize=EIGHTBITS,
            parity=PARITY_NONE,
            stopbits=STOPBITS_ONE,
            **self.options,
        )


__all__ = ["Connection", "TcpConnection", "SerialConnection"]
