"""Contains class that are used for data storage."""

from __future__ import annotations

from typing import Dict, List

from .exceptions import FrameTypeError
from .factory import FrameFactory
from .frame import Request


class FrameBucket:
    """Keeps track of frame versions and stores versioning data.

    Attributes:
        versions -- dictionary containing frame versions
    """

    def __init__(self, versions: Dict[int, int] = None):
        """Created FrameBucket instance.

        Keyword arguments:
            versions -- dictionary containing frame versions
        """
        self.versions = {}
        self._queue: List[Request] = []

        if versions is not None:
            self.versions = versions

    def __len__(self) -> int:
        """Gets number of stored frame versions."""
        return len(self.versions)

    def __repr__(self) -> str:
        """Returns serializable string representation."""
        return f"""FrameBucket(
    versions: {self.versions}
)
"""

    def fill(self, frames: Dict[int, int]) -> None:
        """Fills storage with frame versions.

        Keyword arguments:
            frames -- dictionary of frames keyed by frame versions
        """
        for type_, version in frames.items():
            if type_ not in self.versions or self.versions[type_] != version:
                # We don't have this frame or it's version has changed.
                self.update(type_, version)

    def update(self, type_: int, version: int) -> None:
        """Schedules frame update.

        Keyword arguments:
            type_ -- type of frame
            version -- new frame version to update to
        """
        try:
            frame = FrameFactory().get_frame(type_=type_)
        except FrameTypeError:
            return None

        if not isinstance(frame, Request):
            # Do not process responses.
            return None

        self.versions[type_] = version
        self._queue.append(frame)
        return None

    @property
    def queue(self) -> list[Request]:
        """Clears and returns changed frames queue."""
        queue = self._queue
        self._queue = []
        return queue
