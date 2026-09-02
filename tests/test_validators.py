"""Phone number normalisation and per-provider length rules.

All numbers here are synthetic.
"""

import pytest

from bot.services.providers import Provider
from bot.services.validators import (
    Reason,
    normalize,
    validate,
)

KBZ = Provider.KBZPAY
WAVE = Provider.WAVEPAY


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # Already national format.
        ("09123456789", "09123456789"),
        # Punctuation people actually type.
        ("09 123 456 789", "09123456789"),
        ("09-123-456-789", "09123456789"),
        ("(09) 123 456 789", "09123456789"),
        ("09.123.456.789", "09123456789"),
        ("  09123456789  ", "09123456789"),
        # International forms.
        ("+959123456789", "09123456789"),
        ("+95 9 123 456 789", "09123456789"),
        ("00959123456789", "09123456789"),
        ("959123456789", "09123456789"),
        # Country code written in front of an already-national number.
        ("+9509123456789", "09123456789"),
        # Dropped trunk zero.
        ("9123456789", "09123456789"),
        # Legacy lengths that were never withdrawn.
        ("0912345678", "0912345678"),
        ("091234567", "091234567"),
        ("+95912345678", "0912345678"),
    ],
)
def test_normalize_accepts_the_forms_people_type(raw, expected):
    assert normalize(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "abc",
        "09abc456789",
        "0912345678901",  # 13 digits
        "0912345",  # 7 digits, too short to be a mobile
        "01234567",  # landline NDC
        "011234567",  # Yangon landline, valid number but not a mobile
        "09123456789 09987654321",  # two numbers at once
        "08123456789",  # wrong mobile NDC
    ],
)
def test_normalize_rejects_non_mobile_input(raw):
    assert normalize(raw) is None


def test_explicit_country_code_disambiguates_a_leading_959():
    """9591234567 is ambiguous; the user's own prefix decides which reading wins."""
    # With "+", the 95 is a country code: 95|91234567 -> 091234567.
    assert normalize("+959 123 4567") == "091234567"
    # Without it, the leading 9 is a dropped trunk zero: 0|9591234567.
    assert normalize("9591234567") == "09591234567"


@pytest.mark.parametrize(
    "raw",
    [
        "09960476\u00b2\u00b23",  # superscript two
        "0912345678\u2075",  # superscript five
        "\u0660\u0669\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669",  # Arabic-Indic
    ],
)
def test_unicode_digits_are_rejected_not_crashed(raw):
    """str.isdigit() accepts these; the BCD encoder cannot. Reject before it explodes."""
    check = validate(raw, WAVE)
    assert not check.ok
    assert check.reason is Reason.NOT_DIGITS


@pytest.mark.parametrize("raw", ["", "   ", "\n"])
def test_empty_input(raw):
    assert validate(raw, WAVE).reason is Reason.EMPTY


@pytest.mark.parametrize("length,raw", [(11, "09123456789"), (10, "0912345678"), (9, "091234567")])
def test_wavepay_accepts_every_valid_mobile_length(length, raw):
    check = validate(raw, WAVE)
    assert check.ok
    assert check.phone == raw
    assert check.digits == length


def test_kbzpay_accepts_11_digits():
    check = validate("09123456789", KBZ)
    assert check.ok
    assert check.phone == "09123456789"


@pytest.mark.parametrize("raw", ["0912345678", "091234567"])
def test_kbzpay_rejects_short_numbers_by_default(raw):
    """The BCD field holds 11 digits; padding shorter ones is unverified."""
    check = validate(raw, KBZ)
    assert not check.ok
    assert check.reason is Reason.KBZPAY_NEEDS_11
    assert check.digits == len(raw)


@pytest.mark.parametrize("raw", ["0912345678", "091234567"])
def test_kbzpay_short_numbers_pass_when_the_flag_is_on(monkeypatch, raw):
    monkeypatch.setattr("bot.config.KBZPAY_ALLOW_SHORT_NUMBERS", True)
    check = validate(raw, KBZ)
    assert check.ok
    assert check.phone == raw


def test_a_number_that_is_not_a_mobile_reports_its_digit_count():
    check = validate("0912345", WAVE)
    assert check.reason is Reason.NOT_MYANMAR_MOBILE
    assert check.digits == 7
