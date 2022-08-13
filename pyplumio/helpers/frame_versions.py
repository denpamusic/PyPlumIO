"""Contains frame versions storage helper."""
from __future__ import annotations

from typing import TYPE_CHECKING, Final

from pyplumio.frames import get_frame_handler, is_known_frame_type
from pyplumio.helpers.factory import factory
from pyplumio.helpers.typing import VersionsInfoType

if TYPE_CHECKING:
    from pyplumio.devices import Device

DEFAULT_FRAME_VERSION: Final = 0


class FrameVersions:
    """Represents frame versions storage."""

    versions: VersionsInfoType
    device: Device

    def __init__(self, device: Device):
        """Initialize Frame Versions object."""
        self.versions = {}
        self.device = device

    async def async_update(self, frame_versions: VersionsInfoType) -> None:
        """Check versions and fetch outdated frames."""
        for frame_type, version in frame_versions.items():
            if is_known_frame_type(frame_type) and (
                frame_type not in self.versions or self.versions[frame_type] != version
            ):
                # We don't have this frame or it's version has changed.
                request = factory(
                    get_frame_handler(frame_type), recipient=self.device.address
                )
                self.device.queue.put_nowait(request)
                self.versions[frame_type] = version
