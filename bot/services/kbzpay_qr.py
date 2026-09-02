"""KBZPay Receive-QR string generator.

Format reverse-engineered from KBZPay 5.8.5 (see kbzpay-qr-notes.html):

    QR = base64(42-byte TLV) + "F" + checksum_char + hex(server_time_ms) + "=="

TLV layout (42 bytes):
    85 06 "KBZPay"            magic header
    61 40 4f 02 f0 50 02 10   template bytes (constant)
    51 02 31 31 57 16
    <6 bytes BCD phone>       11 digits + one 0xD pad nibble
    26 09 10 10 1f 9f 08 04   template bytes (constant)
    01 01 9f 24 01 30

The phone field is fixed width, so the digit count is not free: 11 digits fill it
exactly. Shorter numbers are padded with further 0xD nibbles, which keeps the tail
template aligned but is UNVERIFIED against KBZPay's server — the 42-byte payload
is generated server-side (the app only appends the timestamp suffix), so there is
no client-side encoder to confirm the padding rule from. Callers gate this behind
``config.KBZPAY_ALLOW_SHORT_NUMBERS``.
"""

import base64
import re
import time

BASE64_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"

HEAD = bytes.fromhex("85064b425a50617961404f02f0500210510231315716")
TAIL = bytes.fromhex("260910101f9f080401019f240130")

#: The BCD phone field is 6 bytes, i.e. 12 half-byte digits.
PHONE_FIELD_NIBBLES = 12

#: HEAD (22) + phone field (6) + TAIL (14).
TLV_LENGTH = 42

_ASCII_DIGITS_RE = re.compile(r"[0-9]+")


class KbzPayPayloadError(ValueError):
    """The phone number cannot be packed into KBZPay's fixed-width BCD field."""


def _bcd(phone: str) -> bytes:
    if not _ASCII_DIGITS_RE.fullmatch(phone):
        raise KbzPayPayloadError(f"phone must be ASCII digits only, got {phone!r}")
    if len(phone) > PHONE_FIELD_NIBBLES:
        raise KbzPayPayloadError(
            f"phone has {len(phone)} digits, field holds {PHONE_FIELD_NIBBLES}"
        )
    digits = phone.ljust(PHONE_FIELD_NIBBLES, "D")
    return bytes(int(digits[i : i + 2], 16) for i in range(0, len(digits), 2))


def kbzpay_qr_string(phone: str, ts_ms: int | None = None) -> str:
    ts = ts_ms if ts_ms is not None else int(time.time() * 1000)
    tlv = HEAD + _bcd(phone) + TAIL
    if len(tlv) != TLV_LENGTH:
        # A shifted tail makes the server read a different number, so refuse rather
        # than hand back a QR that points at the wrong account.
        raise KbzPayPayloadError(f"TLV is {len(tlv)} bytes, expected {TLV_LENGTH}")
    payload = base64.b64encode(tlv).decode()
    checksum = BASE64_ALPHABET[sum(int(d) for d in str(ts)) % 64]
    return f"{payload}F{checksum}{ts:x}=="
