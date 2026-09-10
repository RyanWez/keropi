"""Renders the branded QR card.

Layout is plain top-to-bottom: accent bar, provider name, QR, recipient number,
and an optional warning line. Fonts are vendored under bot/assets/fonts so the
output is identical everywhere and a slim container without system fonts still
works.
"""

import io
import logging
from functools import lru_cache
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont
from qrcode.constants import ERROR_CORRECT_H

from bot.services.providers import Provider

logger = logging.getLogger(__name__)

_ASSETS = Path(__file__).resolve().parent.parent / "assets" / "fonts"
_IMAGES = Path(__file__).resolve().parent.parent / "assets" / "images"

# First existing path wins; the vendored copies come first so behaviour does not
# depend on what the host image happens to ship.
SANS_BOLD_CANDIDATES = (
    _ASSETS / "DejaVuSans-Bold.ttf",
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
)
MONO_BOLD_CANDIDATES = (
    _ASSETS / "DejaVuSansMono-Bold.ttf",
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"),
)
# DejaVu has no Myanmar glyphs, so Burmese text drawn with it comes out as boxes.
MYANMAR_BOLD_CANDIDATES = (
    _ASSETS / "NotoSansMyanmar-Bold.ttf",
    Path("/usr/share/fonts/truetype/noto/NotoSansMyanmar-Bold.ttf"),
)

#: Myanmar block, plus the Extended-A and Extended-B ranges.
_MYANMAR_RANGES = ((0x1000, 0x109F), (0xAA60, 0xAA7F), (0xA9E0, 0xA9FF))

CARD_WIDTH = 900
PADDING = 48
GAP = 36
TITLE_SIZE = 56
NUMBER_SIZE = 40
HINT_SIZE = 24
AMOUNT_SIZE = 32
ACCENT_BAR_HEIGHT = 10

PROVIDER_STYLE = {
    Provider.KBZPAY: {
        "label": "KBZ Pay",
        "color": (0, 102, 179),      # KBZ Blue
        "qr_color": (0, 102, 179),   # Blue QR Code
        "logo": _IMAGES / "kbz.png",
    },
    Provider.WAVEPAY: {
        "label": "WavePay",
        "color": (229, 148, 0),      # Wave Yellow/Gold
        "qr_color": (217, 130, 0),   # Rich Yellow/Amber QR Code (high scan contrast)
        "logo": _IMAGES / "wave.png",
    },
}

WARNING_COLOR = (200, 60, 40)


@lru_cache(maxsize=8)
def _font(candidates: tuple[Path, ...], size: int) -> ImageFont.FreeTypeFont:
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    # Better a card with small text than no card at all.
    logger.warning("no font found in %s, falling back to the PIL default", candidates)
    return ImageFont.load_default(size)


def has_myanmar(text: str) -> bool:
    return any(
        any(low <= ord(char) <= high for low, high in _MYANMAR_RANGES) for char in text
    )


def _hint_font(text: str) -> ImageFont.ImageFont:
    """Pick a font that can actually draw ``text``."""
    candidates = MYANMAR_BOLD_CANDIDATES if has_myanmar(text) else SANS_BOLD_CANDIDATES
    return _font(candidates, HINT_SIZE)


@lru_cache(maxsize=len(Provider))
def _provider_logo(provider: Provider) -> Image.Image:
    """Load and trim a provider logo so transparent margins do not affect sizing."""
    path = PROVIDER_STYLE[provider]["logo"]
    with Image.open(path) as source:
        logo = source.convert("RGBA")
    alpha_bounds = logo.getchannel("A").getbbox()
    if alpha_bounds is None:
        raise ValueError(f"provider logo has no visible pixels: {path}")
    return logo.crop(alpha_bounds)


@lru_cache(maxsize=len(Provider) * 2)
def _provider_badge(provider: Provider, backing_size: int) -> Image.Image:
    """Build the small QR-centre badge once for each provider and QR size."""
    logo_size = max(1, round(backing_size * 0.82))
    logo = _provider_logo(provider).copy()
    logo.thumbnail((logo_size, logo_size), Image.Resampling.LANCZOS)

    backing = Image.new("RGBA", (backing_size, backing_size), "white")
    mask = Image.new("L", backing.size, 0)
    mask_draw = ImageDraw.Draw(mask)
    radius = max(4, backing_size // 7)
    mask_draw.rounded_rectangle((0, 0, backing_size - 1, backing_size - 1), radius, fill=255)
    backing.putalpha(mask)

    logo_x = (backing_size - logo.width) // 2
    logo_y = (backing_size - logo.height) // 2
    backing.alpha_composite(logo, (logo_x, logo_y))
    return backing


def _add_provider_logo(qr_img: Image.Image, provider: Provider) -> None:
    """Place a compact logo over the QR while staying inside correction-H capacity."""
    backing_size = max(1, round(qr_img.width * 0.21))
    backing = _provider_badge(provider, backing_size)
    x = (qr_img.width - backing_size) // 2
    y = (qr_img.height - backing_size) // 2
    qr_img.paste(backing, (x, y), backing)


def _wrap(
    text: str, font: ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw
) -> list[str]:
    """Greedy word wrap, so a longer warning cannot run off the edge of the card."""
    words = text.split()
    if not words:
        return []

    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if draw.textlength(candidate, font=font) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def render_qr_card(
    provider: Provider,
    phone: str,
    payload: str,
    warning: str | None = None,
    amount: int | None = None,
) -> bytes:
    """Render the branded QR card and return PNG bytes."""
    style = PROVIDER_STYLE[provider]

    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_H, box_size=12, border=2)
    qr.add_data(payload)
    qr.make(fit=True)
    qr_img = qr.make_image(
        fill_color=style["qr_color"], back_color="white"
    ).convert("RGB")
    # Short payloads (WavePay) produce tiny QRs — upscale to fill the card.
    target = CARD_WIDTH - PADDING * 2
    if qr_img.width < target:
        qr_img = qr_img.resize((target, target), Image.NEAREST)
    _add_provider_logo(qr_img, provider)

    title_font = _font(SANS_BOLD_CANDIDATES, TITLE_SIZE)
    number_font = _font(MONO_BOLD_CANDIDATES, NUMBER_SIZE)
    amount_font = _font(SANS_BOLD_CANDIDATES, AMOUNT_SIZE)
    hint_font = _hint_font(warning or "")
    amount_text = f"{amount:,} MMK" if amount is not None else None

    width = max(CARD_WIDTH, qr_img.width + PADDING * 2)
    text_width = width - PADDING * 2

    measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    warning_lines = _wrap(warning, hint_font, text_width, measure) if warning else []
    line_height = HINT_SIZE + 6

    title_box = measure.textbbox((0, 0), style["label"], font=title_font)
    number_box = measure.textbbox((0, 0), phone, font=number_font)
    amount_box = (
        measure.textbbox((0, 0), amount_text, font=amount_font) if amount_text else None
    )
    title_height = title_box[3] - title_box[1]
    number_height = number_box[3] - number_box[1]
    amount_height = amount_box[3] - amount_box[1] if amount_box else 0

    height = (
        PADDING
        + title_height
        + GAP
        + qr_img.height
        + GAP
        + number_height
        + (GAP // 2 + amount_height if amount_text else 0)
        + (GAP // 2 + line_height * len(warning_lines) if warning_lines else 0)
        + PADDING
    )

    card = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(card)
    draw.rectangle([0, 0, width, ACCENT_BAR_HEIGHT], fill=style["color"])

    def centered(text: str, font: ImageFont.ImageFont, top: int, fill) -> None:
        box = draw.textbbox((0, 0), text, font=font)
        x = (width - (box[2] - box[0])) // 2 - box[0]
        draw.text((x, top - box[1]), text, font=font, fill=fill)

    y = PADDING
    centered(style["label"], title_font, y, style["color"])
    y += title_height + GAP

    card.paste(qr_img, ((width - qr_img.width) // 2, y))
    y += qr_img.height + GAP

    centered(phone, number_font, y, "black")
    y += number_height

    if amount_text:
        y += GAP // 2
        centered(amount_text, amount_font, y, style["color"])
        y += amount_height

    if warning_lines:
        y += GAP // 2
        for line in warning_lines:
            centered(line, hint_font, y, WARNING_COLOR)
            y += line_height

    buf = io.BytesIO()
    card.save(buf, format="PNG")
    return buf.getvalue()


async def render_qr_card_async(
    provider: Provider,
    phone: str,
    payload: str,
    warning: str | None = None,
    amount: int | None = None,
) -> bytes:
    """Render off the event loop.

    Pillow work is ~30 ms of CPU per card. Run inline, it blocks every other update
    for that long; concurrent users end up queued behind each other.
    """
    from bot.services.render_pool import run_in_render_pool

    return await run_in_render_pool(
        render_qr_card,
        provider,
        phone,
        payload,
        warning=warning,
        amount=amount,
    )
