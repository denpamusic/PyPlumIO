"""Contains exceptions."""
from __future__ import annotations


class PyPlumIOError(Exception):
    """Base PyPlumIO error class."""


class ConnectionFailedError(PyPlumIOError):
    """Raised on connection failure."""


class ParameterNotFoundError(PyPlumIOError):
    """Raised when device parameter is not found."""


class UnknownDeviceError(PyPlumIOError):
    """Raised on unsupported device."""


class ReadError(PyPlumIOError):
    """Raised on read error."""


class FrameError(PyPlumIOError):
    """Base class for frame errors."""


class ChecksumError(FrameError):
    """Raised on checksum error while parsing frame content."""


class UnknownFrameError(FrameError):
    """Raised on unknown frame type."""


class FrameDataError(FrameError):
    """Raised on incorrect frame data."""
