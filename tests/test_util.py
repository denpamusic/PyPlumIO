from pyplumio import util


def test_crc():
    assert util.crc(b"\x68\x0a\x00\x00\x56\x30\x05\x40") == 0x41


def test_to_hex():
    assert util.to_hex(b"\xFE\xED\xBE\xEF") == ["FE", "ED", "BE", "EF"]


def test_unpack_ushort():
    assert util.unpack_ushort(b"\x0a\x00") == 10


def test_ip4_to_bytes():
    assert util.ip4_to_bytes("127.0.0.1") == b"\x7f\x00\x00\x01"


def test_ip4_from_bytes():
    assert util.ip4_from_bytes(b"\x7f\x00\x00\x01") == "127.0.0.1"


def test_ip6_from_bytes():
    assert (
        util.ip6_from_bytes(
            b"\xfe\xed\xde\xad\xbe\xef\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01"
        )
        == "feed:dead:beef::1"
    )


def test_ip6_to_bytes():
    assert (
        util.ip6_to_bytes("feed:dead:beef::1")
        == b"\xfe\xed\xde\xad\xbe\xef\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01"
    )


def test_merge_without_override():
    defaults = {"foo": 1}

    data = {"bar": 2}

    assert util.merge(defaults, data) == {"foo": 1, "bar": 2}


def test_merge_with_empty_override():
    defaults = {"foo": 1, "bar": 2}

    data = {"foo": 2}

    assert util.merge(defaults, data) == {"foo": 2, "bar": 2}


def test_merge_with_empty_data():
    defaults = {"foo": 1}

    assert util.merge(defaults, {}) == {"foo": 1}


def test_check_parameter_valid():
    assert util.check_parameter(bytearray([0xFF, 0xFE, 0xFF, 0xFF]))


def test_check_parameter_invalid():
    assert not util.check_parameter(bytearray([0xFF, 0xFF, 0xFF, 0xFF]))
