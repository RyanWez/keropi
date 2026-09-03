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

CARD_WIDTH = 400
PADDING = 36
GAP = 18
TITLE_SIZE = 28
NUMBER_SIZE = 22
HINT_SIZE = 15
ACCENT_BAR_HEIGHT = 6

PROVIDER_STYLE = {
    Provider.KBZPAY: {
        "label": "KBZ Pay",
        "color": (0, 102, 179),      # KBZ Blue
        "qr_color": (0, 102, 179),   # Blue QR Code
    },
    Provider.WAVEPAY: {
        "label": "WavePay",
        "color": (229, 148, 0),      # Wave Yellow/Gold
        "qr_color": (217, 130, 0),   # Rich Yellow/Amber QR Code (high scan contrast)
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
    provider: Provider, phone: str, payload: str, warning: str | None = None
) -> bytes:
    """Render the branded QR card and return PNG bytes."""
    style = PROVIDER_STYLE[provider]

    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_H, box_size=6, border=2)
    qr.add_data(payload)
    qr.make(fit=True)
    qr_img = qr.make_image(
        fill_color=style["qr_color"], back_color="white"
    ).convert("RGB")
    # Normalize QR to fill the card's target width comfortably.
    target = CARD_WIDTH - PADDING * 2
    if qr_img.width != target:
        qr_img = qr_img.resize((target, target), Image.NEAREST)

    title_font = _font(SANS_BOLD_CANDIDATES, TITLE_SIZE)
    number_font = _font(MONO_BOLD_CANDIDATES, NUMBER_SIZE)
    hint_font = _hint_font(warning or "")

    width = max(CARD_WIDTH, qr_img.width + PADDING * 2)
    text_width = width - PADDING * 2

    measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    warning_lines = _wrap(warning, hint_font, text_width, measure) if warning else []
    line_height = HINT_SIZE + 6

    title_box = measure.textbbox((0, 0), style["label"], font=title_font)
    number_box = measure.textbbox((0, 0), phone, font=number_font)
    title_height = title_box[3] - title_box[1]
    number_height = number_box[3] - number_box[1]

    height = (
        PADDING
        + title_height
        + GAP
        + qr_img.height
        + GAP
        + number_height
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

    if warning_lines:
        y += GAP // 2
        for line in warning_lines:
            centered(line, hint_font, y, WARNING_COLOR)
            y += line_height

    buf = io.BytesIO()
    card.save(buf, format="PNG")
    return buf.getvalue()


async def render_qr_card_async(
    provider: Provider, phone: str, payload: str, warning: str | None = None
) -> bytes:
    """Render off the event loop.

    Pillow work is ~30 ms of CPU per card. Run inline, it blocks every other update
    for that long; concurrent users end up queued behind each other.
    """
    from bot.services.render_pool import run_in_render_pool

    return await run_in_render_pool(
        render_qr_card, provider, phone, payload, warning=warning
    )
