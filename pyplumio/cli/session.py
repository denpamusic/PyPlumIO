"""Contains connection session manager for the PyPlumIO CLI."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
import logging
from typing import Any, Final

import pyplumio
from pyplumio.connection import Connection
from pyplumio.const import ATTR_COUNT, ATTR_START, DeviceType
from pyplumio.exceptions import PyPlumIOError
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
        "last_frame_message",
        "last_parameters",
        "last_update_time",
        "product_info",
        "url",
        "_connection",
        "_interval",
        "_on_update",
        "_tasks",
    )

    baudrate: int
    last_frame_message: bytes | None
    last_parameters: list[tuple[int, ParameterValues]] | None
    last_update_time: datetime | None
    product_info: ProductInfo | None
    url: str
    _connection: Connection | None
    _interval: float
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
    ) -> None:
        """Initialize the session."""
        self.url, self.baudrate = url, baudrate
        self.last_frame_message = self.last_parameters = self.last_update_time = None
        self.product_info = self._connection = None
        self._interval, self._on_update, self._tasks = interval, on_update, set()

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
        self._start_tasks()
        return self.product_info

    async def _read_uid(self, timeout: float) -> ProductInfo | None:
        """Read single UID response within timeout."""
        if not self._connection:
            return None
        start = asyncio.get_running_loop().time()
        while (rem := timeout - (asyncio.get_running_loop().time() - start)) > 0:
            try:
                frame = await asyncio.wait_for(
                    self._connection.reader.read(), timeout=rem
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
            try:
                await self._connection.writer.write(
                    requests.UIDRequest(recipient=DeviceType.ECOMAX)
                )
                if info := await self._read_uid(timeout):
                    return info
            except TimeoutError:
                pass
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
        req = requests.EcomaxServiceParametersRequest(
            recipient=DeviceType.ECOMAX, data={ATTR_COUNT: 255, ATTR_START: 0}
        )
        while self._connection:
            try:
                await self._connection.writer.write(req)
                await asyncio.sleep(self._interval)
            except asyncio.CancelledError:
                break
            except Exception:
                _LOGGER.exception("Failed to send service parameters request")

    def _handle_frame(self, frame: Any) -> None:
        """Handle incoming frame if service parameters response."""
        if isinstance(frame, responses.EcomaxServiceParametersResponse) and (
            params := frame.data.get(ATTR_ECOMAX_SERVICE_PARAMETERS)
        ):
            self.last_frame_message, self.last_parameters = frame.message, params
            self.last_update_time = datetime.now(UTC)
            if self._on_update:
                self._on_update(params, frame.message)

    async def _read_loop(self) -> None:
        """Continuously read frames and process service parameters."""
        while self._connection:
            try:
                self._handle_frame(await self._connection.reader.read())
            except pyplumio.ProtocolError:
                continue
            except asyncio.CancelledError:
                break
            except Exception:
                _LOGGER.exception("Error while reading frame")

    async def close(self) -> None:
        """Close connection and stop all running tasks."""
        for task in list(self._tasks):
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
            self._tasks.clear()
        if self._connection:
            await self._connection.close()
            self._connection = None


__all__ = ("Session",)
