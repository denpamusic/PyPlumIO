"""Contains exceptions."""


class ChecksumError(Exception):
    """Raised on checksum error while parsing frame content."""


class LengthError(Exception):
    """Raised on unexpected frame length while parsing frame content."""


class FrameTypeError(Exception):
    """Raised on unknown frame type."""


class VersionError(Exception):
    """Raised on unknown frame version."""


class UninitializedParameterError(Exception):
    """Raised on uninitialized device parameter."""
