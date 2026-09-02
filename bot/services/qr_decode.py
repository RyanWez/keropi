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
    BASE64_ALPHABET,
    HEAD,
    PHONE_FIELD_NIBBLES,
    TAIL,
    TLV_LENGTH,
)

MYANMAR_TZ = timezone(timedelta(hours=6, minutes=30))

_HEX_RE = re.compile(r"[0-9a-f]+")

#: Literal terminator, not base64 padding: 42 bytes encode to 56 characters exactly.
TERMINATOR = "=="
SEPARATOR = "F"

PHONE_FIELD_START = len(HEAD)
PHONE_FIELD_END = PHONE_FIELD_START + PHONE_FIELD_NIBBLES // 2


@dataclass
class Decoded:
    raw: str
    notes: list[str] = field(default_factory=list)
    tlv: bytes | None = None
    phone_digits: str | None = None
    pad_nibbles: str | None = None
    timestamp_ms: int | None = None

    @property
    def looks_like_kbzpay(self) -> bool:
        return self.tlv is not None


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
    """Find where the base64 body ends and the timestamp suffix begins.

    The separator is a literal "F", but base64 bodies contain "F" too and the
    checksum character can itself be a hex digit, so a single regex picks the wrong
    split whenever the checksum happens to be "F". Instead, try every candidate from
    the longest body down and accept the first where the tail is all hex and the body
    decodes. A body whose bytes start with the KBZPay header wins outright.
    """
    if not text.endswith(TERMINATOR):
        return None
    middle = text[: -len(TERMINATOR)]

    fallback: _Split | None = None
    for index in range(len(middle) - 2, -1, -1):
        if middle[index] != SEPARATOR:
            continue
        body, tail = middle[:index], middle[index + 2 :]
        if not tail or not _HEX_RE.fullmatch(tail):
            continue
        tlv = _decode_b64(body)
        if tlv is None:
            continue
        candidate = _Split(
            tlv=tlv,
            checksum=middle[index + 1],
            timestamp_ms=int(tail, 16),
            header_matched=tlv.startswith(HEAD),
        )
        if candidate.header_matched:
            return candidate
        fallback = fallback or candidate
    return fallback


def decode_qr_string(raw: str) -> Decoded:
    """Describe a scanned QR payload, whatever shape it turns out to be."""
    text = raw.strip()
    result = Decoded(raw=text)

    if text.isdigit():
        result.notes.append(
            f"Plain digits ({len(text)}) — this is a WavePay-style payload, "
            "not a KBZPay TLV."
        )
        result.phone_digits = text
        return result

    parsed = _split(text)
    if parsed is None:
        result.notes.append("Does not match base64 + F + checksum + hex(ts) + '=='.")
        return result

    tlv = parsed.tlv
    result.tlv = tlv
    result.timestamp_ms = parsed.timestamp_ms

    if len(tlv) != TLV_LENGTH:
        result.notes.append(
            f"TLV is {len(tlv)} bytes, not the expected {TLV_LENGTH} — "
            "the field layout differs from the known format."
        )
    if not parsed.header_matched:
        result.notes.append("HEAD template does not match.")
    if not tlv.endswith(TAIL):
        result.notes.append("TAIL template does not match.")

    if len(tlv) >= PHONE_FIELD_END:
        digits, pad = _split_bcd(tlv[PHONE_FIELD_START:PHONE_FIELD_END])
        result.phone_digits = digits
        result.pad_nibbles = pad

    expected = BASE64_ALPHABET[sum(int(d) for d in str(parsed.timestamp_ms)) % 64]
    if expected != parsed.checksum:
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
            f"TLV: <b>{len(tlv)} bytes</b> (expected {TLV_LENGTH})",
            f"HEAD ok: {'yes' if tlv.startswith(HEAD) else '<b>NO</b>'}",            f"TAIL ok: {'yes' if tlv.endswith(TAIL) else '<b>NO</b>'}",
            f"phone field [{PHONE_FIELD_START}:{PHONE_FIELD_END}]: "
            f"<code>{tlv[PHONE_FIELD_START:PHONE_FIELD_END].hex()}</code>",
            f"full TLV: <code>{tlv.hex()}</code>",
        ]

    if decoded.phone_digits is not None:
        lines.append(
            f"digits: <code>{decoded.phone_digits}</code> ({len(decoded.phone_digits)})"
        )
    if decoded.pad_nibbles is not None:
        pad = decoded.pad_nibbles.upper() or "none"
        lines.append(f"pad nibbles: <code>{pad}</code> ({len(decoded.pad_nibbles)})")

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
