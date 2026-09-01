"""KBZPay Receive-QR string generator.

Format reverse-engineered from KBZPay 5.8.5 (see ../KBZPay_QR_Research.md):

    QR = base64(42-byte TLV) + "F" + checksum_char + hex(server_time_ms) + "=="

TLV layout (42 bytes):
    85 06 "KBZPay"            magic header
    61 40 4f 02 f0 50 02 10   template bytes (constant)
    51 02 31 31 57 16
    <6 bytes BCD phone>       phone number, odd digit count padded with 0xD
    26 09 10 10 1f 9f 08 04   template bytes (constant)
    01 01 9f 24 01 30
"""

import base64
import time

BASE64_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"

HEAD = bytes.fromhex("85064b425a50617961404f02f0500210510231315716")
TAIL = bytes.fromhex("260910101f9f080401019f240130")


def _bcd(phone: str) -> bytes:
    digits = phone if len(phone) % 2 == 0 else phone + "D"
    return bytes(int(digits[i : i + 2], 16) for i in range(0, len(digits), 2))


def kbzpay_qr_string(phone: str, ts_ms: int | None = None) -> str:
    ts = ts_ms if ts_ms is not None else int(time.time() * 1000)
    tlv = HEAD + _bcd(phone) + TAIL
    payload = base64.b64encode(tlv).decode()
    checksum = BASE64_ALPHABET[sum(int(d) for d in str(ts)) % 64]
    return f"{payload}F{checksum}{ts:x}=="
