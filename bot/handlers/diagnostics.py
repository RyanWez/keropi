"""Owner-only diagnostics.

`/decode` exists to answer one open question: how does KBZPay's server encode a
legacy 9- or 10-digit number into the fixed 6-byte phone field? Send it a photo of
any KBZPay Receive QR and it reports the byte layout. One sample from a legacy
number settles whether KBZPAY_ALLOW_SHORT_NUMBERS can be turned on.

Gated on OWNER_ID because the reports expose the recipient's number and internal
byte layout, and because it would otherwise be a phone-number lookup tool.
"""

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from bot import config
from bot.services.qr_decode import decode_image, decode_qr_string, describe

logger = logging.getLogger(__name__)
router = Router(name="diagnostics")

PROMPT = (
    "🔧 <b>/decode</b>\n\n"
    "Send me a photo of a KBZPay Receive QR (or reply to one), or paste the QR "
    "string directly, and I'll show you its byte layout.\n\n"
    "What I'm after is a QR belonging to a <b>9- or 10-digit</b> number — that "
    "reveals how the server pads the fixed-width phone field, which is the one "
    "thing the app itself doesn't tell us."
)

NOT_DECODED = "Couldn't find a barcode in that image. Try a sharper crop."

MISSING_DEP = (
    "Image decoding needs the <code>zxing-cpp</code> package, which isn't "
    "installed here. Paste the QR string as text instead."
)


def _is_owner(message: Message) -> bool:
    return (
        config.OWNER_ID != 0
        and message.from_user is not None
        and message.from_user.id == config.OWNER_ID
    )


@router.message(Command("decode"), F.func(_is_owner))
async def cmd_decode(message: Message) -> None:
    payload = (message.text or "").removeprefix("/decode").strip()
    replied = message.reply_to_message

    if payload:
        await message.reply(describe(decode_qr_string(payload)))
        return

    if replied is not None and replied.photo:
        await _decode_photo(message, replied)
        return

    await message.reply(PROMPT)


@router.message(F.photo, F.func(_is_owner))
async def owner_photo(message: Message) -> None:
    await _decode_photo(message, message)


async def _decode_photo(message: Message, source: Message) -> None:
    if message.bot is None or not source.photo:
        return

    buffer = await message.bot.download(source.photo[-1].file_id)
    if buffer is None:
        await message.reply(NOT_DECODED)
        return

    try:
        payloads = decode_image(buffer.read())
    except ImportError:
        await message.reply(MISSING_DEP)
        return

    if not payloads:
        await message.reply(NOT_DECODED)
        return

    for payload in payloads:
        await message.reply(describe(decode_qr_string(payload)))
