"""Contains frame versions storage helper."""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from pyplumio.exceptions import UnknownFrameError
from pyplumio.frames import get_frame_handler
from pyplumio.helpers.factory import factory
from pyplumio.helpers.typing import VersionsInfoType

if TYPE_CHECKING:
    from pyplumio.devices import Device


class FrameVersions:
    """Represents frame versions storage."""

    versions: VersionsInfoType
    _queue: asyncio.Queue
    _device: Device

    def __init__(self, queue: asyncio.Queue, device: Device):
        """Initialize Frame Versions object."""
        self.versions = {}
        self._queue = queue
        self._device = device

    def _make_request(self, frame_type: int, version: int) -> None:
        """Make update request and put it into write queue."""
        try:
            request = factory(
                get_frame_handler(frame_type), recipient=self._device.address
            )
        except UnknownFrameError:
            # Ignore unknown frames in version list.
            return

        self._queue.put_nowait(request)
        self.versions[frame_type] = version

    def update(self, frame_versions: VersionsInfoType) -> None:
        """Check versions and fetch outdated frames."""
        for frame_type, version in frame_versions.items():
            if frame_type not in self.versions or self.versions[frame_type] != version:
                # We don't have this frame or it's version has changed.
                self._make_request(frame_type, version)

    async def async_update(self, *args, **kwargs) -> None:
        """Asynchronously check versions and fetch outdated frames."""
        self.update(*args, *kwargs)
