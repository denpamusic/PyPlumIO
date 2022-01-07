"""Contains frame factory class."""

from __future__ import annotations

from .exceptions import FrameTypeError
from .frame import Frame
from .frames import requests, responses


class FrameFactory:
    """Used to create frame objects based on frame class."""

    _types: dict = {
        requests.CheckDevice.type_: requests.CheckDevice,
        requests.ProgramVersion.type_: requests.ProgramVersion,
        requests.UID.type_: responses.UID,
        requests.Password.type_: requests.Password,
        requests.DataStructure.type_: requests.DataStructure,
        requests.Timezones.type_: requests.Timezones,
        requests.Parameters.type_: requests.Parameters,
        requests.MixerParameters.type_: requests.MixerParameters,
        responses.CheckDevice.type_: responses.CheckDevice,
        responses.CurrentData.type_: responses.CurrentData,
        responses.ProgramVersion.type_: responses.ProgramVersion,
        responses.UID.type_: responses.UID,
        responses.Password.type_: responses.Password,
        responses.RegData.type_: responses.RegData,
        responses.DataStructure.type_: responses.DataStructure,
        responses.Timezones.type_: responses.Timezones,
        responses.Parameters.type_: responses.Parameters,
        responses.MixerParameters.type_: responses.MixerParameters,
    }

    @staticmethod
    def get_frame(type_: int, **args) -> Frame:
        """Gets frame by frame type.

        Keyword arguments:
        type -- integer, repsenting frame type
        args -- arguments passed to frame class
        """
        if type_ in FrameFactory._types:
            return FrameFactory._types[type_](**args)

        raise FrameTypeError()
