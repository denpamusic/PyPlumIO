"""Contains exceptions."""

from __future__ import annotations

from pyplumio.const import FrameType


class PyPlumIOError(Exception):
    """Base PyPlumIO error class."""


class ConnectionFailedError(PyPlumIOError):
    """Raised on connection failure."""


class RequestError(PyPlumIOError):
    """Raised on request error."""

    def __init__(self, message: str, frame_type: FrameType) -> None:
        """Initialize a new RequestError."""
        super().__init__(message)
        self.frame_type = frame_type


class ProtocolError(PyPlumIOError):
    """Base class for protocol-related errors."""


class ReadError(ProtocolError):
    """Raised on read error."""


class ChecksumError(ProtocolError):
    """Raised on incorrect frame checksum."""


class UnknownDeviceError(ProtocolError):
    """Raised on unknown device."""


class UnknownFrameError(ProtocolError):
    """Raised on unknown frame type."""


class FrameDataError(ProtocolError):
    """Raised on incorrect frame data."""
