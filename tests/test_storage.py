import pytest

from pyplumio.frames import requests, responses
from pyplumio.storage import FrameBucket


@pytest.fixture()
def frame_bucket():
    return FrameBucket({})


def test_fill_with_nothing(frame_bucket):
    frame_bucket.fill({})
    assert len(frame_bucket) == 0


def test_fill_bucket(frame_bucket):
    frame_bucket.fill({requests.UID.type_: 1, requests.Password.type_: 2})
    assert frame_bucket.versions[requests.UID.type_] == 1


def test_fill_with_same_version(frame_bucket):
    frame_bucket.fill({requests.Password.type_: 2})
    assert frame_bucket.versions[requests.Password.type_] == 2


def test_bucket_update_with_request(frame_bucket):
    frame_bucket.update(type_=requests.UID.type_, version=2)
    found = False
    for frame in frame_bucket.queue:
        if frame.type_ == requests.UID.type_:
            found = True
            break

    assert found


def test_bucket_update_with_response(frame_bucket):
    frame_bucket.update(type_=responses.UID.type_, version=2)
    found = False
    for frame in frame_bucket.queue:
        if frame.type_ == responses.UID.type_:
            found = True
            break

    assert not found
