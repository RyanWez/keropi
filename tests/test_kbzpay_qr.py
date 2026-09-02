"""Locks the KBZPay QR string format down.

The template bytes and the suffix rule were recovered from KBZPay 5.8.5 and
verified against the real app on a device. Nothing here may drift silently:
the phone number lives in a fixed-width field, so a change that shifts the
byte layout produces a QR that resolves to a *different* account rather than
failing loudly.

Phone numbers used below are synthetic.
"""

import base64

import pytest

from bot.services.kbzpay_qr import HEAD, TAIL, KbzPayPayloadError, kbzpay_qr_string

# 1 September 2026 15:56:17 MMT. Digit sum 71, 71 % 64 = 7 -> alphabet[7] = "H".
FROZEN_TS_MS = 1788254777618
FROZEN_TS_HEX = "1a05c4a7112"
FROZEN_CHECKSUM = "H"

TLV_LENGTH = 42
BASE64_LENGTH = 56
PHONE_FIELD = slice(22, 28)


def test_template_bytes_are_pinned():
    """These constants are the whole reverse-engineering result. Never regenerate them."""
    assert HEAD.hex() == "85064b425a50617961404f02f0500210510231315716"
    assert TAIL.hex() == "260910101f9f080401019f240130"
    assert len(HEAD) == 22
    assert len(TAIL) == 14
    assert HEAD[:2] == bytes([0x85, 0x06])
    assert HEAD[2:8] == b"KBZPay"


@pytest.mark.parametrize(
    ("phone", "expected"),
    [
        (
            "09123456789",
            "hQZLQlpQYXlhQE8C8FACEFECMTFXFgkSNFZ4nSYJEBAfnwgEAQGfJAEwFH1a05c4a7112==",
        ),
        (
            "09987654321",
            "hQZLQlpQYXlhQE8C8FACEFECMTFXFgmYdlQyHSYJEBAfnwgEAQGfJAEwFH1a05c4a7112==",
        ),
    ],
)
def test_golden_vector(phone, expected):
    assert kbzpay_qr_string(phone, ts_ms=FROZEN_TS_MS) == expected


def _tlv_of(qr: str) -> bytes:
    head = qr[:BASE64_LENGTH]
    assert len(head) == BASE64_LENGTH
    return base64.b64decode(head)


def test_tlv_is_always_42_bytes():
    """The phone field is fixed width; any other total means the tail has shifted."""
    tlv = _tlv_of(kbzpay_qr_string("09123456789", ts_ms=FROZEN_TS_MS))
    assert len(tlv) == TLV_LENGTH


def test_phone_field_sits_at_offset_22_and_round_trips():
    tlv = _tlv_of(kbzpay_qr_string("09123456789", ts_ms=FROZEN_TS_MS))
    field = tlv[PHONE_FIELD]
    assert len(field) == 6
    # 11 digits + one 0xD pad nibble fills the field exactly.
    assert field.hex() == "09123456789d"
    assert tlv[:22] == HEAD
    assert tlv[28:] == TAIL


def test_suffix_layout():
    qr = kbzpay_qr_string("09123456789", ts_ms=FROZEN_TS_MS)
    suffix = qr[BASE64_LENGTH:]
    assert suffix == f"F{FROZEN_CHECKSUM}{FROZEN_TS_HEX}=="
    # The trailing "==" is a literal terminator, not base64 padding: 42 bytes
    # encode to exactly 56 characters, which needs no padding.
    assert len(base64.b64encode(bytes(TLV_LENGTH))) == BASE64_LENGTH


def test_checksum_tracks_the_timestamp():
    a = kbzpay_qr_string("09123456789", ts_ms=1788254777618)
    b = kbzpay_qr_string("09123456789", ts_ms=1788254777619)
    assert a[:BASE64_LENGTH] == b[:BASE64_LENGTH]
    assert a[BASE64_LENGTH:] != b[BASE64_LENGTH:]


def test_default_timestamp_is_used_when_omitted():
    qr = kbzpay_qr_string("09123456789")
    assert qr.startswith("hQZLQlpQYXlhQE8C8FACEFECMTFXFgkSNFZ4nSYJEBAfnwgEAQGfJAEw")
    assert qr.endswith("==")


@pytest.mark.parametrize(
    ("phone", "expected_bcd"),
    [
        ("09123456789", "09123456789d"),
        ("0912345678", "0912345678dd"),
        ("091234567", "091234567ddd"),
    ],
)
def test_short_numbers_pad_the_field_instead_of_shifting_the_tail(phone, expected_bcd):
    """Whatever the digit count, the field stays 6 bytes and TAIL stays put.

    Before padding was added, a 10-digit number produced a 41-byte TLV and the
    server read the first tail byte as part of the number: 0996047673 came back
    as 099604767326.
    """
    tlv = _tlv_of(kbzpay_qr_string(phone, ts_ms=FROZEN_TS_MS))
    assert len(tlv) == TLV_LENGTH
    assert tlv[PHONE_FIELD].hex() == expected_bcd
    assert tlv[28:] == TAIL


def test_too_many_digits_is_refused():
    with pytest.raises(KbzPayPayloadError):
        kbzpay_qr_string("0912345678901")


@pytest.mark.parametrize("phone", ["09960476\u00b2\u00b23", "09abc456789", ""])
def test_non_ascii_digits_are_refused_not_crashed(phone):
    """int(..., 16) used to raise a bare ValueError deep inside the encoder."""
    with pytest.raises(KbzPayPayloadError):
        kbzpay_qr_string(phone)
