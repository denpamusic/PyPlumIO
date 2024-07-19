"""Contains exceptions."""

from __future__ import annotations


class PyPlumIOError(Exception):
    """Base PyPlumIO error class."""


class ConnectionFailedError(PyPlumIOError):
    """Raised on connection failure."""


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
