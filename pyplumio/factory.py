"""Contains frame factory class."""

from __future__ import annotations

import inspect

from .exceptions import FrameTypeError
from .frame import Frame
from .frames import requests, responses
from .helpers.singleton import Singleton


class FrameFactory(Singleton):
    """Used to create frame objects based on frame class."""

    def __init__(self) -> None:
        """Calls method to make type list."""
        self._types = {}

    def get_frame(self, type_: int, **kwargs) -> Frame:
        """Gets frame by frame type.

        Keyword arguments:
        type -- integer that represents frame type
        kwargs -- keywords arguments to pass to the frame class
        """
        if type_ in self.types:
            return self.types[type_](**kwargs)

        raise FrameTypeError()

    @property
    def types(self) -> dict:
        """Constructs and return a list of available frame
        types and handlers.
        """
        if not self._types:
            for module in [requests, responses]:
                for _, obj in inspect.getmembers(module, inspect.isclass):
                    if obj.__module__ == module.__name__:
                        # Object is within the module.
                        self._types[obj.type_] = obj

        return self._types
