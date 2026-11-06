"""Contains connection session manager for the PyPlumIO CLI."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import suppress
from datetime import UTC, datetime
import logging
from typing import Any, Final

import pyplumio
from pyplumio.connection import Connection
from pyplumio.const import ATTR_COUNT, ATTR_START, DeviceType
from pyplumio.exceptions import (
    ChecksumError,
    FrameDataError,
    PyPlumIOError,
    ReadError,
    UnknownDeviceError,
    UnknownFrameError,
)
from pyplumio.frames import requests, responses
from pyplumio.parameters import ParameterValues
from pyplumio.protocol import DummyProtocol
from pyplumio.structures.ecomax_service_parameters import ATTR_ECOMAX_SERVICE_PARAMETERS
from pyplumio.structures.product_info import ATTR_PRODUCT, ProductInfo

_LOGGER = logging.getLogger(__name__)

DEFAULT_RETRIES: Final = 3
DEFAULT_TIMEOUT: Final = 5.0


class Session:
    """Manages connection and communication with ecoMAX controller."""

    __slots__ = (
        "baudrate",
        "connected",
        "last_frame_message",
        "last_parameters",
        "last_update_time",
        "product_info",
        "url",
        "_connection",
        "_interval",
        "_on_disconnect",
        "_on_update",
        "_tasks",
    )

    baudrate: int
    connected: bool
    last_frame_message: bytes | None
    last_parameters: list[tuple[int, ParameterValues]] | None
    last_update_time: datetime | None
    product_info: ProductInfo | None
    url: str
    _connection: Connection | None
    _interval: float
    _on_disconnect: Callable[[str], None] | None
    _on_update: Callable[[list[tuple[int, ParameterValues]], bytes], None] | None
    _tasks: set[asyncio.Task[None]]

    def __init__(
        self,
        url: str,
        baudrate: int = 115200,
        interval: float = 2.0,
        on_update: (
            Callable[[list[tuple[int, ParameterValues]], bytes], None] | None
        ) = None,
        on_disconnect: Callable[[str], None] | None = None,
    ) -> None:
        """Initialize the session."""
        self.url, self.baudrate = url, baudrate
        self.connected = False
        self.last_frame_message = self.last_parameters = self.last_update_time = None
        self.product_info = self._connection = None
        self._interval = interval
        self._on_update = on_update
        self._on_disconnect = on_disconnect
        self._tasks = set()

    def _handle_disconnect(self, reason: str) -> None:
        """Handle connection disconnect."""
        if not self.connected:
            return
        self.connected = False
        for task in list(self._tasks):
            if task is not asyncio.current_task():
                task.cancel()
        if self._on_disconnect:
            self._on_disconnect(reason)

    async def connect(
        self, retries: int = DEFAULT_RETRIES, timeout: float = DEFAULT_TIMEOUT
    ) -> ProductInfo:
        """Connect to device and obtain product info."""
        self._connection = pyplumio.serial_for_url(
            self.url,
            protocol=DummyProtocol(),
            reconnect_on_failure=False,
            baudrate=self.baudrate,
        )
        await self._connection.connect()
        self.product_info = await self._fetch_product_info(retries, timeout)
        self.connected = True
        self._start_tasks()
        return self.product_info

    async def _read_uid(self, timeout: float) -> ProductInfo | None:
        """Read single UID response within timeout."""
        if not self._connection:
            return None
        start = asyncio.get_running_loop().time()
        while (
            remaining_time := timeout - (asyncio.get_running_loop().time() - start)
        ) > 0:
            try:
                frame = await asyncio.wait_for(
                    self._connection.reader.read(), timeout=remaining_time
                )
                if isinstance(frame, responses.UIDResponse) and isinstance(
                    product := frame.data.get(ATTR_PRODUCT), ProductInfo
                ):
                    return product
            except pyplumio.ProtocolError:
                continue
        return None

    async def _fetch_product_info(self, retries: int, timeout: float) -> ProductInfo:
        """Fetch product info with retries and timeout."""
        for attempt in range(retries):
            if not self._connection:
                break
            with suppress(TimeoutError):
                await self._connection.writer.write(
                    requests.UIDRequest(recipient=DeviceType.ECOMAX)
                )
                if product_info := await self._read_uid(timeout):
                    return product_info
            _LOGGER.warning("UID attempt %d/%d timed out", attempt + 1, retries)
        raise PyPlumIOError(f"Failed to retrieve product info after {retries} retries")

    def _start_tasks(self) -> None:
        """Start polling and reading background tasks."""
        for coro in (self._poll_loop(), self._read_loop()):
            task = asyncio.create_task(coro)
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

    async def _poll_loop(self) -> None:
        """Periodically send service parameters request."""
        request = requests.EcomaxServiceParametersRequest(
            recipient=DeviceType.ECOMAX, data={ATTR_COUNT: 255, ATTR_START: 0}
        )
        while self.connected and self._connection:
            try:
                await self._connection.writer.write(request)
            except (OSError, ReadError) as err:
                self._handle_disconnect(str(err) or "Connection lost")
                break
            finally:
                await asyncio.sleep(self._interval)

    def _handle_frame(self, frame: Any) -> None:
        """Handle incoming frame if service parameters response."""
        if isinstance(frame, responses.EcomaxServiceParametersResponse) and (
            parameters := frame.data.get(ATTR_ECOMAX_SERVICE_PARAMETERS)
        ):
            self.last_frame_message = frame.message
            self.last_parameters = parameters
            self.last_update_time = datetime.now(UTC)
            if self._on_update:
                self._on_update(parameters, frame.message)

    async def _read_loop(self) -> None:
        """Continuously read frames and process service parameters."""
        while self.connected and self._connection:
            try:
                self._handle_frame(await self._connection.reader.read())
            except (
                ChecksumError,
                UnknownDeviceError,
                UnknownFrameError,
                FrameDataError,
            ) as err:
                _LOGGER.debug("Skipping recoverable protocol error: %s", err)
                continue
            except (OSError, ReadError) as err:
                self._handle_disconnect(str(err) or "Connection lost")
                break

    async def close(self) -> None:
        """Close connection and stop all running tasks."""
        self.connected = False
        for task in list(self._tasks):
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
            self._tasks.clear()
        if self._connection:
            await self._connection.close()
            self._connection = None


__all__ = ("Session",)
