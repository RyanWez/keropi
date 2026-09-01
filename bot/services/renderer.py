import io
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont
from qrcode.constants import ERROR_CORRECT_H

from bot.services.providers import Provider

FONT_BOLD = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
FONT_MONO_BOLD = Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf")

# Card layout in pixels at 4x scale; final image is downscaled for smooth edges.
SCALE = 4
CARD_WIDTH = 900 * SCALE // 4
PADDING = 48
TITLE_SIZE = 56
NUMBER_SIZE = 40
HINT_SIZE = 24

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


def _font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def render_qr_card(provider: Provider, phone: str, payload: str, warning: str | None = None) -> bytes:
    """Render the branded QR card and return PNG bytes."""
    style = PROVIDER_STYLE[provider]

    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_H, box_size=12, border=2)
    qr.add_data(payload)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color=style["qr_color"], back_color="white").convert("RGB")
    # Short payloads (WavePay) produce tiny QRs — upscale to fill the card.
    target = CARD_WIDTH - PADDING * 2
    if qr_img.width < target:
        qr_img = qr_img.resize((target, target), Image.NEAREST)

    title_font = _font(FONT_BOLD, TITLE_SIZE)
    number_font = _font(FONT_MONO_BOLD, NUMBER_SIZE)
    hint_font = _font(FONT_BOLD, HINT_SIZE)

    tmp = ImageDraw.Draw(qr_img)
    title_box = tmp.textbbox((0, 0), style["label"], font=title_font)
    number_box = tmp.textbbox((0, 0), phone, font=number_font)
    warn_text = warning or ""
    warn_box = tmp.textbbox((0, 0), warn_text, font=hint_font) if warn_text else None

    gap = 36
    width = max(CARD_WIDTH, qr_img.width + PADDING * 2)
    height = (
        PADDING
        + (title_box[3] - title_box[1])
        + gap
        + qr_img.height
        + gap
        + (number_box[3] - number_box[1])
        + (gap // 2 + (warn_box[3] - warn_box[1]) if warn_text else 0)
        + PADDING
    )

    card = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(card)
    # Colored accent bar across the top of the card.
    draw.rectangle([0, 0, width, 10], fill=style["color"])

    def center(text: str, font: ImageFont.FreeTypeFont, y: int) -> None:
        box = draw.textbbox((0, 0), text, font=font)
        draw.text(((width - (box[2] - box[0])) // 2 - box[0], y), text, font=font, fill="black")

    draw.text(
        ((width - (title_box[2] - title_box[0])) // 2, PADDING),
        style["label"],
        font=title_font,
        fill=style["color"],
    )

    y = PADDING + (title_box[3] - title_box[1]) + gap
    card.paste(qr_img, ((width - qr_img.width) // 2, y))
    y += qr_img.height + gap

    center(phone, number_font, y)
    y += number_box[3] - number_box[1]
    if warn_text:
        y += gap // 2
        box = draw.textbbox((0, 0), warn_text, font=hint_font)
        draw.text(
            ((width - (box[2] - box[0])) // 2, y), warn_text, font=hint_font, fill=(200, 60, 40)
        )

    buf = io.BytesIO()
    card.save(buf, format="PNG")
    return buf.getvalue()
