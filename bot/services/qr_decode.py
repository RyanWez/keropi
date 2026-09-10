"""Takes a KBZPay QR apart again.

The reason this exists: KBZPay's 42-byte payload is built by their server, not by
the app, so there is no client-side encoder to read the padding rule from. The only
way to learn how a legacy 9- or 10-digit number is encoded is to look at a real
Receive QR belonging to such an account.

A Receive QR is meant to be shown to strangers, so asking someone for a screenshot
of theirs costs nothing and — unlike a test transfer — moves no money.
"""

import base64
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from bot.services.kbzpay_qr import (
    AMOUNT_TAG,
    BASE64_ALPHABET,
    MAGIC,
    PHONE_FIELD_NIBBLES,
    PHONE_TAG,
    ROUTE,
    TLV_LENGTH,
)

MYANMAR_TZ = timezone(timedelta(hours=6, minutes=30))

_HEX_RE = re.compile(r"[0-9a-f]+")
_SUFFIX_RE = re.compile(r"(?P<checksum>[A-Za-z0-9+/])(?P<timestamp>[0-9a-f]+)={0,2}$")

PHONE_FIELD_BYTES = PHONE_FIELD_NIBBLES // 2


@dataclass
class Decoded:
    raw: str
    notes: list[str] = field(default_factory=list)
    tlv: bytes | None = None
    qr_type: str | None = None
    phone_digits: str | None = None
    pad_nibbles: str | None = None
    amount_text: str | None = None
    amount_mmk: int | None = None
    timestamp_ms: int | None = None
    checksum_valid: bool | None = None
    phone_field_start: int | None = None
    phone_field_end: int | None = None

    @property
    def looks_like_kbzpay(self) -> bool:
        return self.tlv is not None and self.tlv.startswith(MAGIC)


def _split_bcd(field_bytes: bytes) -> tuple[str, str]:
    """Return (decimal digits, trailing pad nibbles) for a BCD field."""
    nibbles = field_bytes.hex()
    digits = nibbles.rstrip("abcdef")
    return digits, nibbles[len(digits) :]


def _decode_b64(body: str) -> bytes | None:
    try:
        return base64.b64decode(body + "=" * (-len(body) % 4), validate=True)
    except (ValueError, base64.binascii.Error):
        return None


@dataclass
class _Split:
    tlv: bytes
    checksum: str
    timestamp_ms: int
    header_matched: bool


def _split(text: str) -> _Split | None:
    """Find the KBZ body before ``F + checksum + hex timestamp``.

    Real KBZ samples vary in final padding: the base64 body can end in ``=`` or
    ``==``, and the complete string may or may not have another trailing ``==``.
    Trying every literal F also handles F characters inside base64 and an F checksum.
    """
    candidates: list[_Split] = []
    for index in range(len(text) - 2, -1, -1):
        if text[index] != "F":
            continue
        match = _SUFFIX_RE.fullmatch(text[index + 1 :])
        if match is None:
            continue
        tlv = _decode_b64(text[:index])
        if tlv is None:
            continue
        candidates.append(
            _Split(
                tlv=tlv,
                checksum=match.group("checksum"),
                timestamp_ms=int(match.group("timestamp"), 16),
                header_matched=tlv.startswith(MAGIC),
            )
        )

    matching = [candidate for candidate in candidates if candidate.header_matched]
    if matching:
        return max(matching, key=lambda candidate: len(candidate.tlv))
    return max(candidates, key=lambda candidate: len(candidate.tlv), default=None)


def _parse_kbz_fields(result: Decoded, tlv: bytes) -> None:
    if len(tlv) < 16 or not tlv.startswith(MAGIC):
        result.notes.append("KBZPay magic header does not match.")
        return

    if tlv[8] != 0x61:
        result.notes.append("Payload length marker 0x61 is missing.")
    else:
        expected_length = (len(tlv) - 10) * 2
        if tlv[9] != expected_length:
            result.notes.append(
                f"Length byte is 0x{tlv[9]:02x}, expected 0x{expected_length:02x}."
            )

    if tlv[10:16] != ROUTE:
        result.notes.append("KBZPay route template does not match.")

    phone_tag_at = tlv.find(PHONE_TAG, 16)
    if phone_tag_at < 0 or phone_tag_at + 2 + PHONE_FIELD_BYTES > len(tlv):
        result.notes.append("Phone field marker is missing or truncated.")
    else:
        start = phone_tag_at + len(PHONE_TAG)
        end = start + PHONE_FIELD_BYTES
        digits, pad = _split_bcd(tlv[start:end])
        if not digits.isdigit() or any(char != "d" for char in pad):
            result.notes.append("Phone BCD field contains unexpected nibbles.")
        else:
            result.phone_digits = digits
            result.pad_nibbles = pad
            result.phone_field_start = start
            result.phone_field_end = end

    amount_tag_at = tlv.find(AMOUNT_TAG, max(16, phone_tag_at))
    if amount_tag_at < 0 or amount_tag_at + 3 > len(tlv):
        result.notes.append("Amount field marker is missing or truncated.")
        return

    amount_length = tlv[amount_tag_at + 2]
    amount_start = amount_tag_at + 3
    amount_end = amount_start + amount_length
    if amount_end != len(tlv):
        result.notes.append(
            f"Amount field ends at byte {amount_end}, payload ends at {len(tlv)}."
        )
        return

    try:
        amount_text = tlv[amount_start:amount_end].decode("ascii")
    except UnicodeDecodeError:
        result.notes.append("Amount field is not ASCII.")
        return

    result.amount_text = amount_text
    if amount_text == "0":
        result.qr_type = "receive"
    elif re.fullmatch(r"[1-9][0-9]*\.0", amount_text):
        result.amount_mmk = int(amount_text[:-2])
        result.qr_type = "bill" if b"\x51\x04Bill" in tlv else "amount"
    else:
        result.qr_type = "unknown"
        result.notes.append(f"Amount value {amount_text!r} has an unknown format.")


def decode_qr_string(raw: str) -> Decoded:
    """Describe a scanned QR payload, including known variable KBZPay variants."""
    text = raw.strip()
    result = Decoded(raw=text)

    if text.isdigit():
        result.qr_type = "wavepay"
        result.notes.append(
            f"Plain digits ({len(text)}) — this is a WavePay-style payload, "
            "not a KBZPay TLV."
        )
        result.phone_digits = text
        return result

    parsed = _split(text)
    if parsed is None:
        result.notes.append("Does not match a KBZPay base64 + timestamp payload.")
        return result

    result.tlv = parsed.tlv
    result.timestamp_ms = parsed.timestamp_ms
    _parse_kbz_fields(result, parsed.tlv)

    expected = BASE64_ALPHABET[sum(int(d) for d in str(parsed.timestamp_ms)) % 64]
    result.checksum_valid = expected == parsed.checksum
    if not result.checksum_valid:
        result.notes.append(
            f"Checksum is {parsed.checksum!r}, recomputed {expected!r}."
        )
    return result


def describe(decoded: Decoded) -> str:
    """Render a decode result as the HTML report the owner sees."""
    lines = ["🔍 <b>QR decode</b>", f"<code>{decoded.raw[:120]}</code>", ""]

    if decoded.tlv is not None:
        tlv = decoded.tlv
        lines += [
            f"type: <b>{decoded.qr_type or 'unknown'}</b>",
            f"TLV: <b>{len(tlv)} bytes</b>",
            f"magic ok: {'yes' if tlv.startswith(MAGIC) else '<b>NO</b>'}",
            f"full TLV: <code>{tlv.hex()}</code>",
        ]
        if decoded.phone_field_start is not None and decoded.phone_field_end is not None:
            lines.append(
                f"phone field [{decoded.phone_field_start}:{decoded.phone_field_end}]: "
                f"<code>{tlv[decoded.phone_field_start:decoded.phone_field_end].hex()}</code>"
            )

    if decoded.phone_digits is not None:
        lines.append(
            f"digits: <code>{decoded.phone_digits}</code> ({len(decoded.phone_digits)})"
        )
    if decoded.pad_nibbles is not None:
        pad = decoded.pad_nibbles.upper() or "none"
        lines.append(f"pad nibbles: <code>{pad}</code> ({len(decoded.pad_nibbles)})")
    if decoded.amount_text is not None:
        amount = (
            f"{decoded.amount_mmk:,} MMK"
            if decoded.amount_mmk is not None
            else decoded.amount_text
        )
        lines.append(f"amount: <code>{amount}</code>")

    if decoded.timestamp_ms is not None:
        stamp = datetime.fromtimestamp(decoded.timestamp_ms / 1000, MYANMAR_TZ)
        lines.append(f"timestamp: {stamp:%Y-%m-%d %H:%M:%S} MMT")

    if decoded.notes:
        lines += ["", "⚠️ " + "\n⚠️ ".join(decoded.notes)]

    if decoded.pad_nibbles and len(decoded.phone_digits or "") != 11:
        lines += [
            "",
            "<b>This is the sample worth having.</b> A non-11-digit number in a "
            f"{len(decoded.tlv or b'')}-byte payload padded with "
            f"<code>{decoded.pad_nibbles.upper()}</code> confirms the rule — "
            "set KBZPAY_ALLOW_SHORT_NUMBERS once it matches what the bot produces.",
        ]

    return "\n".join(lines)


def decode_image(data: bytes) -> list[str]:
    """Read every barcode in a PNG/JPEG. Empty list if none decode.

    zxing-cpp is imported here so a deployment without it still runs; only this
    command stops working.
    """
    import io

    import zxingcpp
    from PIL import Image

    with Image.open(io.BytesIO(data)) as image:
        return [result.text for result in zxingcpp.read_barcodes(image.convert("RGB"))]
