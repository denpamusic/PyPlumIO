"""Contains class that are used for data storage."""

from __future__ import annotations

from .exceptions import FrameTypeError
from .factory import FrameFactory
from .stream import FrameWriter


class FrameBucket:
    """Keeps track of frame versions and stores versioning data."""

    versions: dict = {}

    def __init__(self, versions: dict = None):
        """Created FrameBucket instance.

        Keyword arguments:
        versions -- dictionary containing frame versions
        """
        if versions is not None:
            self.versions = versions

    def __len__(self):
        """Gets number of versioned frames."""
        return len(self.versions)

    def fill(self, writer: FrameWriter, frames: dict) -> None:
        """Fills storage with frame versions.

        Keyword arguments:
        frames -- dictionary of frames keyed by frame versions
        """
        for type_, version in frames.items():
            if type_ not in self.versions or self.versions[type_] != version:
                # We don't have this frame or it's version has changed.
                self.update(writer, type_, version)

    def update(self, writer: FrameWriter, type_: int, version: int) -> None:
        """Schedules frame update.

        Keyword arguments:
        type_ -- type of frame
        version -- new frame version to update to
        """
        try:
            frame = FrameFactory().get_frame(type_=type_)
            if frame.__module__.split(".")[-1] == "requests":
                # Do not process responses.
                self.versions[type_] = version
                writer.queue(frame)
        except FrameTypeError:
            pass
