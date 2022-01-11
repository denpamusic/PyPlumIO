from pyplumio import util


def test_crc():
    assert util.crc(b"\x68\x0a\x00\x00\x56\x30\x05\x40") == 0x41


def test_to_hex():
    assert util.to_hex(b"\xFE\xED\xBE\xEF") == ["FE", "ED", "BE", "EF"]


def test_unpack_ushort():
    assert util.unpack_ushort(b"\x0a\x00") == 10


def test_ip_to_bytes():
    assert util.ip_to_bytes("127.0.0.1") == b"\x7f\x00\x00\x01"


def test_ip_from_bytes():
    assert util.ip_from_bytes(b"\x7f\x00\x00\x01") == "127.0.0.1"


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


def test_uid_stamp():
    uid_bytes = b"\x00\x16\x00\x11\x0D\x38\x33\x38\x36\x55\x39".decode()
    assert util.uid_stamp(uid_bytes) == "\x14\xD1"


def test_uid_5bits_to_char():
    numbers = (
        0,
        16,
        5,
        0,
        16,
        8,
        20,
        1,
        24,
        25,
        12,
        16,
        3,
        27,
        20,
        10,
        25,
        1,
        5,
        2,
        13,
    )
    assert (
        "".join([util.uid_5bits_to_char(x) for x in numbers]) == "0G50G8K1ZPCG3RKAP152D"
    )


def test_uid_5bits_to_char_with_out_of_range():
    numbers = (33, -1)
    assert "".join([util.uid_5bits_to_char(x) for x in numbers]) == "##"
