"""Contains connection session manager for the PyPlumIO CLI."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from contextlib import suppress
from datetime import UTC, datetime
import logging
from typing import Final, TypeVar, cast

from serialx import SerialException

import pyplumio
from pyplumio.connection import DEFAULT_BAUDRATE, RECONNECT_AFTER_SECONDS, Connection
from pyplumio.const import ATTR_COUNT, ATTR_START, DeviceType
from pyplumio.exceptions import (
    ConnectionFailedError,
    ProtocolError,
    PyPlumIOError,
    ReadError,
)
from pyplumio.frames import Frame, requests, responses
from pyplumio.helpers.task_manager import TaskManager
from pyplumio.parameters import ParameterValues
from pyplumio.protocol import DummyProtocol
from pyplumio.structures.ecomax_service_parameters import ATTR_ECOMAX_SERVICE_PARAMETERS
from pyplumio.structures.product_info import ATTR_PRODUCT, ProductInfo

_LOGGER = logging.getLogger(__name__)

DEFAULT_INTERVAL_SECONDS: Final = 2.0
DEFAULT_RETRIES: Final = 3
DEFAULT_TIMEOUT_SECONDS: Final = 5.0

UID_REQUEST: Final = requests.UIDRequest(recipient=DeviceType.ECOMAX)
SERVICE_PARAMETERS_REQUEST: Final = requests.EcomaxServiceParametersRequest(
    recipient=DeviceType.ECOMAX,
    data={ATTR_COUNT: 255, ATTR_START: 0},
)

_ResultT = TypeVar("_ResultT")


class Session(TaskManager):
    """Represents a connection session with an ecoMAX controller."""

    __slots__ = (
        "baudrate",
        "last_frame_message",
        "last_parameters",
        "last_update_time",
        "product_info",
        "url",
        "_connection",
        "_interval",
        "_on_status",
        "_on_update",
    )

    baudrate: int
    last_frame_message: bytes | None
    last_parameters: Sequence[tuple[int, ParameterValues]] | None
    last_update_time: datetime | None
    product_info: ProductInfo | None
    url: str
    _connection: Connection | None
    _interval: float
    _on_status: Callable[[str], None] | None
    _on_update: Callable[[Sequence[tuple[int, ParameterValues]]], None] | None

    def __init__(
        self,
        url: str,
        baudrate: int = DEFAULT_BAUDRATE,
        interval: float = DEFAULT_INTERVAL_SECONDS,
        on_update: Callable[[Sequence[tuple[int, ParameterValues]]], None]
        | None = None,
        on_status: Callable[[str], None] | None = None,
    ) -> None:
        """Initialize the session."""
        super().__init__()
        self.baudrate = baudrate
        self.last_frame_message = None
        self.last_parameters = None
        self.last_update_time = None
        self.product_info = None
        self.url = url
        self._connection = None
        self._interval = interval
        self._on_status = on_status
        self._on_update = on_update

    async def connect(
        self,
        retries: int = DEFAULT_RETRIES,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> ProductInfo:
        """Connect to device and obtain product info."""
        protocol = DummyProtocol()
        protocol.on_connection_lost.add(self._handle_disconnect)
        self._connection = pyplumio.serial_for_url(
            self.url,
            protocol=protocol,
            reconnect_on_failure=False,
            baudrate=self.baudrate,
        )
        self._report_status(f"Connecting to {self.url}...")
        await self._connection.connect()
        self.product_info = await self._request_with_retries(
            UID_REQUEST,
            self._extract_product_info,
            label="product info",
            error_message=f"Failed to retrieve product info after {retries} retries",
            retries=retries,
            timeout=timeout,
        )
        parameters = await self._request_with_retries(
            SERVICE_PARAMETERS_REQUEST,
            self._extract_service_parameters,
            label="service parameters",
            status_label=f"service parameters for {self.product_info.model}",
            error_message=(
                f"{self.product_info.model} did not return service parameters after "
                f"{retries} attempts; this controller may not support them"
            ),
            retries=retries,
            timeout=timeout,
        )
        self._report_status(f"Received {len(parameters)} service parameters.")
        self._start_loops()
        return self.product_info

    async def close(self) -> None:
        """Close connection and stop all running tasks."""
        self.cancel_tasks()
        await self.wait_until_done()
        if self._connection:
            await self._connection.close()
            self._connection = None

    def _report_status(self, message: str) -> None:
        """Report status message via callback if set."""
        if self._on_status:
            self._on_status(message)

    def _start_loops(self) -> None:
        """Start background polling and reading tasks."""
        self.create_task(self._poll_loop())
        self.create_task(self._read_loop())

    async def _reconnect(self) -> None:
        """Reconnect to device in background."""
        connection = cast(Connection, self._connection)
        while True:
            await asyncio.sleep(RECONNECT_AFTER_SECONDS)
            with suppress(ConnectionFailedError, SerialException):
                await connection.connect()
                _LOGGER.warning("Connection restored.")
                self._start_loops()
                break

    async def _handle_disconnect(self) -> None:
        """Handle connection disconnect."""
        self.cancel_tasks()
        _LOGGER.error("Connection lost. Reconnecting in background...")
        self.create_task(self._reconnect())

    async def _read_until(
        self,
        matcher: Callable[[Frame], _ResultT | None],
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> _ResultT | None:
        """Read until matcher returns a value."""
        connection = cast(Connection, self._connection)
        async with asyncio.timeout(timeout):
            while self.connected:
                try:
                    frame = cast(Frame, await connection.reader.read())
                    if (result := matcher(frame)) is not None:
                        return result
                except ProtocolError:
                    continue

            return None

    @staticmethod
    def _extract_product_info(frame: Frame) -> ProductInfo | None:
        """Extract product info from UID response."""
        if isinstance(frame, responses.UIDResponse) and isinstance(
            product := frame.data.get(ATTR_PRODUCT), ProductInfo
        ):
            return product

        return None

    def _extract_service_parameters(
        self, frame: Frame
    ) -> Sequence[tuple[int, ParameterValues]] | None:
        """Extract service parameters from incoming frame."""
        if (
            isinstance(frame, responses.EcomaxServiceParametersResponse)
            and isinstance(
                parameters := frame.data.get(ATTR_ECOMAX_SERVICE_PARAMETERS),
                Sequence,
            )
            and parameters
        ):
            self.last_frame_message = frame.message
            self.last_parameters = parameters
            self.last_update_time = datetime.now(UTC)
            if self._on_update:
                self._on_update(parameters)

            return parameters

        return None

    async def _request_with_retries(
        self,
        request: Frame,
        matcher: Callable[[Frame], _ResultT | None],
        *,
        label: str,
        status_label: str | None = None,
        error_message: str,
        retries: int = DEFAULT_RETRIES,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> _ResultT:
        """Send request and wait for a matching response with retries."""
        connection = cast(Connection, self._connection)
        target = status_label or label
        for attempt in range(retries):
            self._report_status(f"Requesting {target} ({attempt + 1}/{retries})...")
            with suppress(TimeoutError):
                await connection.writer.write(request)
                if (
                    result := await self._read_until(matcher, timeout=timeout)
                ) is not None:
                    return result

            if not self.connected:
                raise PyPlumIOError(f"Connection lost while requesting {label}")

            _LOGGER.warning(
                "%s attempt %i/%i timed out",
                label.capitalize(),
                attempt + 1,
                retries,
            )

        raise PyPlumIOError(error_message)

    async def _poll_loop(self) -> None:
        """Periodically send service parameters request."""
        connection = cast(Connection, self._connection)
        while self.connected:
            try:
                await connection.writer.write(SERVICE_PARAMETERS_REQUEST)
            except (OSError, ReadError):
                await connection.connection_lost()
                break
            await asyncio.sleep(self._interval)

    async def _read_loop(self) -> None:
        """Continuously read frames and process service parameters."""
        connection = cast(Connection, self._connection)
        while self.connected:
            try:
                frame = cast(Frame, await connection.reader.read())
                self._extract_service_parameters(frame)
            except (OSError, ReadError, TimeoutError):
                await connection.connection_lost()
                break
            except ProtocolError as err:
                _LOGGER.debug("Skipping recoverable protocol error: %s", err)

    @property
    def connected(self) -> bool:
        """Return True if session is connected."""
        return self._connection is not None and self._connection.connected.is_set()


__all__ = (
    "DEFAULT_INTERVAL_SECONDS",
    "Session",
)
