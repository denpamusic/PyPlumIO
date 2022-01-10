"""Contains frame factory class."""

from __future__ import annotations

import inspect

from .exceptions import FrameTypeError
from .frame import Frame
from .frames import requests, responses


class FrameFactory:
    """Used to create frame objects based on frame class."""

    _types: dict = {}

    def __new__(cls: str) -> FrameFactory:
        """Implements singleton pattern.

        Keyword arguments:
        cls - current class name
        """
        if not hasattr(cls, "instance"):
            cls.instance = super(FrameFactory, cls).__new__(cls)

        return cls.instance

    def __init__(self) -> None:
        """Calls method to make type list."""
        self.types()

    def types(self) -> dict:
        """Constructs and return a list of available frame
        types and handlers.
        """
        if not self._types:
            ignores = ["Request"]
            for module in [requests, responses]:
                for _, obj in inspect.getmembers(module, inspect.isclass):
                    if (
                        obj.__module__ == module.__name__
                        and obj.__name__ not in ignores
                    ):
                        # Object is within the module and not ignored.
                        self._types[obj.type_] = obj

        return self._types

    def get_frame(self, type_: int, **kwargs) -> Frame:
        """Gets frame by frame type.

        Keyword arguments:
        type -- integer, repsenting frame type
        kwargs -- keywords arguments to pass to the frame class
        """
        if type_ in self._types:
            return self._types[type_](**kwargs)

        raise FrameTypeError()
