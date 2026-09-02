"""Renders a card and scans it back, so a layout change cannot quietly break scanning."""

import io

import pytest
from PIL import Image

from bot.services.kbzpay_qr import kbzpay_qr_string
from bot.services.providers import Provider
from bot.services.renderer import CARD_WIDTH, render_qr_card
from bot.services.wavepay_qr import wavepay_qr_string

zxingcpp = pytest.importorskip("zxingcpp", reason="zxing-cpp is a dev dependency")

PHONE = "09123456789"


def _decode(png: bytes) -> str:
    results = zxingcpp.read_barcodes(Image.open(io.BytesIO(png)))
    assert len(results) == 1, f"expected exactly one barcode, decoded {len(results)}"
    return results[0].text


@pytest.mark.parametrize("provider", list(Provider))
def test_rendered_card_scans_back_to_the_payload(provider):
    payload = (
        kbzpay_qr_string(PHONE)
        if provider is Provider.KBZPAY
        else wavepay_qr_string(PHONE)
    )
    assert _decode(render_qr_card(provider, PHONE, payload)) == payload


def test_wavepay_payload_is_the_bare_number():
    assert wavepay_qr_string(PHONE) == PHONE


@pytest.mark.parametrize("provider", list(Provider))
def test_card_is_png_and_at_least_card_width(provider):
    payload = (
        kbzpay_qr_string(PHONE)
        if provider is Provider.KBZPAY
        else wavepay_qr_string(PHONE)
    )
    image = Image.open(io.BytesIO(render_qr_card(provider, PHONE, payload)))
    assert image.format == "PNG"
    assert image.width >= CARD_WIDTH
    assert image.height > image.width, "the card is portrait: title, QR, then number"


def test_warning_line_grows_the_card_without_breaking_the_scan():
    payload = kbzpay_qr_string(PHONE)
    plain = render_qr_card(Provider.KBZPAY, PHONE, payload)
    warned = render_qr_card(Provider.KBZPAY, PHONE, payload, warning="double-check this")

    assert Image.open(io.BytesIO(warned)).height > Image.open(io.BytesIO(plain)).height
    assert _decode(warned) == payload
