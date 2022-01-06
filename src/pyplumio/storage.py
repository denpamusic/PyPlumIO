from __future__ import annotations

from .exceptions import FrameTypeError
from .factory import FrameFactory
from .stream import FrameWriter


class FrameBucket:
    """ """

    versions: dict = {}

    def __init__(self, writer: FrameWriter):
        self.writer = writer

    def __len__(self):
        return len(self.versions)

    def fill(self, frames: dict) -> None:
        for type, version in frames.items():
            if (not type in self.versions
                or self.versions[type] != version):
                # We don't have this frame or it's version has changed.
                self.update(type, version)

    def update(self, type_: int, version: int) -> None:
        try:
            frame = FrameFactory.get_frame(type)
            if frame.__module__ == 'frames.requests':
                # Do not process responses.
                self.versions[type_] = version
                self.writer.queue(frame)
        except FrameTypeError:
            pass