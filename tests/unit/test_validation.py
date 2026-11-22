import pytest

from ares_mcp.config import Settings
from ares_mcp.errors import InvalidInputError
from ares_mcp.validation import Register, check_paging, normalize_ico, parse_register

REGISTER_CODES = ["vr", "res", "rzp", "nrpzs", "rpsh", "rcns", "szr", "rs", "ros", "ceu"]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("27082440", "27082440"),
        ("270 82 440", "27082440"),
        (" 123456 ", "00123456"),
        ("123456", "00123456"),
        ("1", "00000001"),
        ("0", "00000000"),
        ("00000001", "00000001"),
    ],
)
def test_normalize_ico_accepts_and_pads(raw, expected):
    assert normalize_ico(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", "12ab", "123456789", "abcdefgh", "12-34"])
def test_normalize_ico_rejects_bad_input(raw):
    with pytest.raises(InvalidInputError) as exc:
        normalize_ico(raw)
    assert "8 digits" in str(exc.value)
    assert "[invalid_input]" in str(exc.value)


def test_normalize_ico_does_not_check_check_digit():
    # 12345678 fails the modulo-11 check but must still be accepted.
    assert normalize_ico("12345678") == "12345678"


@pytest.mark.parametrize("code", REGISTER_CODES)
def test_parse_register_accepts_all_ten(code):
    assert parse_register(code) is Register(code)
    assert parse_register(code).value == code


def test_register_enum_has_exactly_ten_codes():
    assert [r.value for r in Register] == REGISTER_CODES


@pytest.mark.parametrize("raw", ["", "xx", "VR", "vr ", "ekonomicke-subjekty-vr"])
def test_parse_register_rejects_unknown_and_lists_codes(raw):
    with pytest.raises(InvalidInputError) as exc:
        parse_register(raw)
    message = str(exc.value)
    assert "[invalid_input]" in message
    for code in REGISTER_CODES:
        assert code in message


@pytest.fixture
def settings():
    return Settings()


def test_check_paging_defaults(settings):
    assert check_paging(None, None, settings) == (0, 20)


def test_check_paging_accepts_valid(settings):
    assert check_paging(40, 100, settings) == (40, 100)
    assert check_paging(0, 1, settings) == (0, 1)


@pytest.mark.parametrize(("start", "count"), [(-1, 10), (0, 0), (0, -1)])
def test_check_paging_rejects_out_of_range(settings, start, count):
    with pytest.raises(InvalidInputError) as exc:
        check_paging(start, count, settings)
    assert "[invalid_input]" in str(exc.value)


def test_check_paging_rejects_above_max_and_states_maximum(settings):
    with pytest.raises(InvalidInputError) as exc:
        check_paging(0, 101, settings)
    assert "100" in str(exc.value)


def test_check_paging_max_is_configurable():
    custom = Settings(max_count=10, default_count=5)
    assert check_paging(None, None, custom) == (0, 5)
    with pytest.raises(InvalidInputError) as exc:
        check_paging(0, 11, custom)
    assert "10" in str(exc.value)
