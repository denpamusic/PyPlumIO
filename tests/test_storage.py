import pytest

from pyplumio.frame import Frame
from pyplumio.frames import requests, responses
from pyplumio.storage import FrameBucket
from pyplumio.stream import FrameWriter


class MockStreamWriter:
    """Mock StreamWriter class representation."""


class MockFrameWriter(FrameWriter):
    """Mock FrameWriter class representation."""

    frames = []

    def __init__(self, writer=MockStreamWriter):
        super().__init__(writer)

    def queue(self, frame: Frame):
        self.frames.append(frame)


@pytest.fixture
def frame_writer():
    return MockFrameWriter()


@pytest.fixture
def frame_bucket():
    return FrameBucket()


def test_fill_with_nothing(frame_bucket, frame_writer):
    frame_bucket.fill(frame_writer, {})
    assert len(frame_bucket) == 0


def test_fill_bucket(frame_bucket, frame_writer):
    frame_bucket.fill(frame_writer, {requests.UID.type_: 1, requests.Password.type_: 2})
    assert frame_bucket.versions[requests.UID.type_] == 1


def test_fill_with_same_version(frame_bucket, frame_writer):
    frame_bucket.fill(frame_writer, {requests.Password.type_: 2})
    assert frame_bucket.versions[requests.Password.type_] == 2


def test_bucket_len(frame_bucket):
    assert len(frame_bucket) == 2


def test_bucket_update_with_request(frame_bucket, frame_writer):
    frame_bucket.update(frame_writer, type_=requests.UID.type_, version=2)
    found = False
    for frame in frame_writer.frames:
        if frame.type_ == requests.UID.type_:
            found = True
            break

    assert found


def test_bucket_update_with_response(frame_bucket, frame_writer):
    frame_bucket.update(frame_writer, type_=responses.UID.type_, version=2)
    found = False
    for frame in frame_writer.frames:
        if frame.type_ == responses.UID.type_:
            found = True
            break

    assert not found
