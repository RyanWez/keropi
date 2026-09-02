"""End-to-end: render a card, scan the image, decode the payload.

This is the loop /decode will run on a real screenshot, so exercising it against
our own output catches a decoder that only works on hand-built strings.

All numbers here are synthetic.
"""

import pytest

from bot.services.kbzpay_qr import kbzpay_qr_string
from bot.services.providers import Provider
from bot.services.qr_decode import decode_image, decode_qr_string
from bot.services.renderer import render_qr_card
from bot.services.wavepay_qr import wavepay_qr_string

pytest.importorskip("zxingcpp", reason="zxing-cpp is needed to read the image back")


@pytest.mark.parametrize("phone", ["09123456789", "0912345678", "091234567"])
def test_kbzpay_card_scans_and_decodes(phone):
    payload = kbzpay_qr_string(phone)
    png = render_qr_card(Provider.KBZPAY, phone, payload)

    (scanned,) = decode_image(png)
    assert scanned == payload

    decoded = decode_qr_string(scanned)
    assert decoded.looks_like_kbzpay
    assert len(decoded.tlv) == 42
    assert decoded.phone_digits == phone
    assert decoded.notes == []


def test_wavepay_card_scans_and_is_recognised_as_plain_digits():
    phone = "09123456789"
    png = render_qr_card(Provider.WAVEPAY, phone, wavepay_qr_string(phone))

    (scanned,) = decode_image(png)
    decoded = decode_qr_string(scanned)

    assert not decoded.looks_like_kbzpay
    assert decoded.phone_digits == phone
