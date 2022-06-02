"""Contains frame factory class."""

from __future__ import annotations

import inspect
from types import ModuleType
from typing import Dict, Type

from .exceptions import FrameTypeError
from .frames import Frame, messages, requests, responses
from .helpers.singleton import Singleton


class FrameFactory(Singleton):
    """Used to create frame objects based on frame class.

    Attributes:
        _types -- frame handlers mapped by frame type
    """

    def __init__(self) -> None:
        """Calls method to make type list."""
        self._types: Dict[int, Type[Frame]] = {}

    def get_frame(self, frame_type: int, **kwargs) -> Frame:
        """Gets frame by frame type.

        Keyword arguments:
            type -- integer that represents frame type
            kwargs -- keywords arguments to pass to the frame class
        """
        if frame_type in self.types:
            return self.types[frame_type](**kwargs)

        raise FrameTypeError(f"Unknown frame type: {frame_type}.")

    def _load_types_from_module(self, module: ModuleType) -> None:
        """Loads types from the module.

        Keyword arguments:
            module - a module to load types from
        """
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if cls.__module__ == module.__name__ and issubclass(cls, Frame):
                # Class is within the module.
                self._types[cls.frame_type] = cls

    @property
    def types(self) -> Dict[int, Type[Frame]]:
        """Constructs and return a list of available frame
        types and handlers.
        """
        if not self._types:
            for module in (requests, responses, messages):
                self._load_types_from_module(module)

        return self._types
