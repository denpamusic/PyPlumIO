"""Contains class that are used for data storage."""

from __future__ import annotations

from typing import Dict, Final, List, Tuple, Type

from .exceptions import FrameTypeError
from .factory import FrameFactory
from .frames import BROADCAST_ADDRESS, Request

DEFAULT_VERSION: Final = 0


class FrameBucket:
    """Keeps track of frame versions and stores versioning data.

    Attributes:
        _address -- address of device that contains this frame bucket
        versions -- dictionary containing frame versions
    """

    def __init__(
        self,
        address: int = BROADCAST_ADDRESS,
        versions: Dict[int, int] = None,
        required: Tuple[Type[Request], ...] = None,
    ):
        """Created FrameBucket instance.

        Keyword arguments:
            versions -- dictionary containing frame versions
        """
        self.versions: Dict[int, int] = {}
        self._address = address
        self._queue: List[Request] = []
        if versions is not None:
            self.fill(versions)

        if required is not None:
            self.fill({frame.frame_type: DEFAULT_VERSION for frame in required})

    def __len__(self) -> int:
        """Gets number of stored frame versions."""
        return len(self.versions)

    def __repr__(self) -> str:
        """Returns serializable string representation."""
        return f"""FrameBucket(
    address: {self._address},
    versions: {self.versions}
)
"""

    def fill(self, frames: Dict[int, int]) -> None:
        """Fills storage with frame versions.

        Keyword arguments:
            frames -- dictionary of frames keyed by frame versions
        """
        for frame_type, version in frames.items():
            if frame_type not in self.versions or self.versions[frame_type] != version:
                # We don't have this frame or it's version has changed.
                self.update(frame_type, version)

    def update(self, frame_type: int, version: int) -> None:
        """Schedules frame update.

        Keyword arguments:
            frame_type -- type of frame
            version -- new frame version to update to
        """
        try:
            frame = FrameFactory().get_frame(
                frame_type=frame_type, recipient=self._address
            )
        except FrameTypeError:
            return None

        if not isinstance(frame, Request):
            # Do not process responses.
            return None

        self.versions[frame_type] = version
        self._queue.append(frame)
        return None

    @property
    def queue(self) -> list[Request]:
        """Clears and returns changed frames queue."""
        queue = self._queue
        self._queue = []
        return queue
