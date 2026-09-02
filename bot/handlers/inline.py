"""Inline mode: `@thebot 09xxxxxxxxx` from inside any chat.

Inline results can only point at a URL or a file_id; no inline result type accepts
raw bytes. So a card has to exist on Telegram's servers before it can be offered,
which is why this needs QR_CACHE_CHAT_ID — somewhere to upload it once. After that
the file_id cache does the work, and repeat numbers answer without any upload.

Both providers are offered as separate results, so there is no provider to pick
first. KBZPay only appears for 11-digit numbers, for the same reason it does in the
private chat.
"""

import asyncio
import logging

from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import (
    BufferedInputFile,
    InlineQuery,
    InlineQueryResultsButton,
    InlineQueryResultCachedPhoto,
)

from bot import config, texts
from bot.services.kbzpay_qr import kbzpay_qr_string
from bot.services.providers import Provider
from bot.services.qr_cache import cache
from bot.services.renderer import render_qr_card_async
from bot.services.validators import PROVIDER_LABELS, needs_padding_warning, validate
from bot.services.wavepay_qr import wavepay_qr_string

logger = logging.getLogger(__name__)
router = Router(name="inline")

#: Results are per-user and cheap to rebuild; don't let Telegram serve them to others.
CACHE_TIME = 60


async def _result(
    query: InlineQuery, provider: Provider, phone: str
) -> InlineQueryResultCachedPhoto | None:
    """Build one result, uploading the card first if it isn't cached yet."""
    warning = texts.PADDING_WARNING if needs_padding_warning(provider, phone) else None
    file_id = cache.get(provider, phone, warning)

    if file_id is None:
        if query.bot is None:
            return None
        payload = (
            kbzpay_qr_string(phone)
            if provider is Provider.KBZPAY
            else wavepay_qr_string(phone)
        )
        png = await render_qr_card_async(provider, phone, payload, warning=warning)
        try:
            sent = await query.bot.send_photo(
                config.QR_CACHE_CHAT_ID,
                BufferedInputFile(png, filename=f"{provider.value}_{phone}.png"),
                caption=f"inline cache · {provider.value} · {phone}",
            )
        except TelegramAPIError:
            logger.warning(
                "could not upload to QR_CACHE_CHAT_ID=%s", config.QR_CACHE_CHAT_ID,
                exc_info=True,
            )
            return None
        if not sent.photo:
            return None
        file_id = sent.photo[-1].file_id
        cache.put(provider, phone, file_id, warning)

    label = PROVIDER_LABELS[provider]
    return InlineQueryResultCachedPhoto(
        id=f"{provider.value}:{phone}",
        photo_file_id=file_id,
        title=label,
        description=f"{label} QR for {phone}",
        caption=texts.QR_CAPTION.format(label=label, phone=phone),
    )


@router.inline_query()
async def inline_qr(query: InlineQuery) -> None:
    open_bot = InlineQueryResultsButton(text=texts.INLINE_OPEN_BOT, start_parameter="start")

    if config.QR_CACHE_CHAT_ID == 0:
        logger.warning("inline mode used but QR_CACHE_CHAT_ID is not set")
        await query.answer([], cache_time=CACHE_TIME, button=open_bot)
        return

    text = query.query.strip()
    if not text:
        await query.answer(
            [], cache_time=CACHE_TIME, is_personal=True,
            button=InlineQueryResultsButton(text=texts.INLINE_PROMPT, start_parameter="start"),
        )
        return

    # Ask each provider separately: a 9- or 10-digit number is valid for WavePay
    # and refused by KBZPay, and both answers are useful.
    accepted = [
        (provider, check.phone)
        for provider in Provider
        if (check := validate(text, provider)).ok
    ]
    if not accepted:
        await query.answer(
            [], cache_time=CACHE_TIME, is_personal=True,
            button=InlineQueryResultsButton(text=texts.INLINE_BAD_NUMBER, start_parameter="start"),
        )
        return

    built = await asyncio.gather(
        *(_result(query, provider, phone) for provider, phone in accepted)
    )
    results = [result for result in built if result is not None]
    if not results:
        await query.answer([], cache_time=0, is_personal=True, button=open_bot)
        return

    await query.answer(results, cache_time=CACHE_TIME, is_personal=True)
