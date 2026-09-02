"""The /decode diagnostic: pulling a KBZPay QR back apart.

All numbers here are synthetic.
"""

from bot.services.kbzpay_qr import kbzpay_qr_string
from bot.services.qr_decode import decode_qr_string, describe

FROZEN_TS_MS = 1788254777618


def test_round_trips_an_11_digit_qr():
    decoded = decode_qr_string(kbzpay_qr_string("09123456789", ts_ms=FROZEN_TS_MS))

    assert decoded.looks_like_kbzpay
    assert len(decoded.tlv) == 42
    assert decoded.phone_digits == "09123456789"
    assert decoded.pad_nibbles == "d"
    assert decoded.timestamp_ms == FROZEN_TS_MS
    assert decoded.notes == []


def test_reports_the_padding_of_a_short_number():
    """This is the shape a legacy-number sample would confirm or contradict."""
    decoded = decode_qr_string(kbzpay_qr_string("091234567", ts_ms=FROZEN_TS_MS))

    assert decoded.phone_digits == "091234567"
    assert decoded.pad_nibbles == "ddd"
    assert len(decoded.tlv) == 42


def test_recognises_a_wavepay_payload():
    decoded = decode_qr_string("09123456789")

    assert not decoded.looks_like_kbzpay
    assert decoded.phone_digits == "09123456789"
    assert "WavePay-style" in decoded.notes[0]


def test_flags_a_broken_checksum():
    qr = kbzpay_qr_string("09123456789", ts_ms=FROZEN_TS_MS)
    tampered = qr[:57] + ("Z" if qr[57] != "Z" else "Y") + qr[58:]

    decoded = decode_qr_string(tampered)
    assert any("Checksum" in note for note in decoded.notes)


def test_flags_an_unparseable_string():
    decoded = decode_qr_string("https://example.com/not-a-payment-qr")

    assert not decoded.looks_like_kbzpay
    assert decoded.notes


def test_finds_the_right_split_when_the_checksum_is_also_an_f():
    """The separator is "F" and the checksum can be "F" too.

    A greedy regex swallowed the separator in that case, leaving a 57-character
    base64 body that would not decode. Timestamp 1788254777616 has a digit sum of
    69, and 69 % 64 = 5, which is "F" in the base64 alphabet.
    """
    qr = kbzpay_qr_string("09123456789", ts_ms=1788254777616)
    assert qr[56:58] == "FF", "this vector only exercises the bug if both are F"

    decoded = decode_qr_string(qr)
    assert decoded.phone_digits == "09123456789"
    assert len(decoded.tlv) == 42
    assert decoded.notes == []


def test_finds_the_right_split_across_many_timestamps():
    for offset in range(0, 4000, 137):
        qr = kbzpay_qr_string("09123456789", ts_ms=1788254777618 + offset)
        decoded = decode_qr_string(qr)
        assert decoded.notes == [], f"failed on {qr}"
        assert decoded.phone_digits == "09123456789"


def test_describe_mentions_the_flag_for_a_short_sample():
    report = describe(decode_qr_string(kbzpay_qr_string("091234567")))
    assert "KBZPAY_ALLOW_SHORT_NUMBERS" in report


def test_describe_is_quiet_for_an_ordinary_sample():
    report = describe(decode_qr_string(kbzpay_qr_string("09123456789")))
    assert "KBZPAY_ALLOW_SHORT_NUMBERS" not in report
    assert "42 bytes" in report
