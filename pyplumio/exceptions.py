"""Contains exceptions."""


class PyPlumIOError(Exception):
    """Base PyPlumIO error class."""


class ConnectionFailedError(PyPlumIOError):
    """Raised on connection failure."""


class UninitializedParameterError(PyPlumIOError):
    """Raised on uninitialized device parameter."""


class FrameError(PyPlumIOError):
    """Base class for frame errors."""


class ChecksumError(FrameError):
    """Raised on checksum error while parsing frame content."""


class LengthError(FrameError):
    """Raised on unexpected frame length while parsing frame content."""


class VersionError(FrameError):
    """Raised on unknown frame version."""


class FrameTypeError(FrameError):
    """Raised on unknown frame type."""
