"""Test PyPlumIO version storage bucket."""

from pyplumio.frames import requests, responses
from pyplumio.storage import DEFAULT_VERSION, FrameBucket


def test_fill_with_nothing(frame_bucket: FrameBucket) -> None:
    """Test filling bucket with empty data."""
    frame_bucket.fill({})
    assert len(frame_bucket) == 0


def test_fill_bucket(frame_bucket: FrameBucket) -> None:
    """Test filling buckit with requests."""
    frame_bucket.fill({requests.UID.frame_type: 1, requests.Password.frame_type: 2})
    assert frame_bucket.versions[requests.UID.frame_type] == 1


def test_fill_bucket_in_init() -> None:
    """Test filling bucket using init function."""
    frame_bucket = FrameBucket(versions={requests.UID.frame_type: 1})
    assert frame_bucket.versions[requests.UID.frame_type] == 1


def test_fill_bucket_required() -> None:
    """Test filling required frames."""
    frame_bucket = FrameBucket(required=(requests.UID, requests.Password))
    assert frame_bucket.versions[requests.UID.frame_type] == DEFAULT_VERSION


def test_repr(frame_bucket: FrameBucket) -> None:
    """Test bucket serializable representation."""
    assert """FrameBucket(
    address: 0,
    versions: {}
)
""" == repr(
        frame_bucket
    )


def test_fill_with_same_version(frame_bucket: FrameBucket) -> None:
    """Test fill bucket with request having same version number."""
    frame_bucket.fill({requests.Password.frame_type: 2})
    assert frame_bucket.versions[requests.Password.frame_type] == 2


def test_bucket_update_with_request(frame_bucket: FrameBucket) -> None:
    """Test update bucket with request having different version."""
    frame_bucket.update(frame_type=requests.UID.frame_type, version=2)
    assert [x for x in frame_bucket.queue if x.frame_type == requests.UID.frame_type]


def test_bucket_update_with_response(frame_bucket: FrameBucket) -> None:
    """Test update bucket with response instead of request."""
    frame_bucket.update(frame_type=responses.UID.frame_type, version=2)
    assert not [
        x for x in frame_bucket.queue if x.frame_type == responses.UID.frame_type
    ]
