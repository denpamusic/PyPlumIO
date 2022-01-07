"""Contains class that are used for data storage."""

from __future__ import annotations

from .exceptions import FrameTypeError
from .factory import FrameFactory
from .stream import FrameWriter


class FrameBucket:
    """Keeps track of frame versions and stores versioning data."""

    versions: dict = {}

    def __init__(self, writer: FrameWriter):
        """Created FrameBucket instance.

        Keyword Argu
        writer -- instance of FrameWriter. Used to schedule updates
        """
        self.writer = writer

    def __len__(self):
        """Gets number of versioned frames."""
        return len(self.versions)

    def fill(self, frames: dict) -> None:
        """Fills storage with frame versions.

        Keyword arguments:
        frames -- dictionary of frames keyed by frame versions
        """
        for type_, version in frames.items():
            if (not type_ in self.versions
                or self.versions[type] != version):
                # We don't have this frame or it's version has changed.
                self.update(type, version)

    def update(self, type_: int, version: int) -> None:
        """Schedules frame update.

        Keyword arguments:
        type_ -- type of frame
        version -- new frame version to update to
        """
        try:
            frame = FrameFactory.get_frame(type)
            if frame.__module__ == 'frames.requests':
                # Do not process responses.
                self.versions[type_] = version
                self.writer.queue(frame)
        except FrameTypeError:
            pass
