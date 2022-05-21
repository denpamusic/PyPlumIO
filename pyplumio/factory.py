"""Contains frame factory class."""

from __future__ import annotations

import inspect
from types import ModuleType
from typing import Dict, Type

from . import requests, responses
from .exceptions import FrameTypeError
from .frame import Frame
from .helpers.singleton import Singleton


class FrameFactory(Singleton):
    """Used to create frame objects based on frame class.

    Attributes:
        _types -- frame handlers mapped by frame type
    """

    def __init__(self) -> None:
        """Calls method to make type list."""
        self._types: Dict[int, Type[Frame]] = {}

    def get_frame(self, type_: int, **kwargs) -> Frame:
        """Gets frame by frame type.

        Keyword arguments:
            type -- integer that represents frame type
            kwargs -- keywords arguments to pass to the frame class
        """
        if type_ in self.types:
            return self.types[type_](**kwargs)

        raise FrameTypeError(f"Unknown frame type: {type_}.")

    def _load_types_from_module(self, module: ModuleType) -> None:
        """Loads types from the module.

        Keyword arguments:
            module - a module to load types from
        """
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if cls.__module__ == module.__name__:
                # Class is within the module.
                self._types[cls.type_] = cls

    @property
    def types(self) -> Dict[int, Type[Frame]]:
        """Constructs and return a list of available frame
        types and handlers.
        """
        if not self._types:
            for module in (requests, responses):
                self._load_types_from_module(module)

        return self._types
