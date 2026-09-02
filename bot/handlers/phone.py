import logging

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, Message

from bot import texts
from bot.keyboards.provider_kb import provider_keyboard
from bot.services.kbzpay_qr import kbzpay_qr_string
from bot.services.providers import Provider
from bot.services.qr_cache import cache
from bot.services.renderer import render_qr_card_async
from bot.services.validators import PROVIDER_LABELS, needs_padding_warning, validate
from bot.services.wavepay_qr import wavepay_qr_string

logger = logging.getLogger(__name__)
router = Router()

# These two handlers are catch-alls. In a group with privacy mode off they would
# answer every message posted, so keep them to one-to-one chats; the commands in
# start.py still work anywhere.
router.message.filter(F.chat.type == ChatType.PRIVATE)


def build_payload(provider: Provider, phone: str) -> str:
    if provider is Provider.KBZPAY:
        return kbzpay_qr_string(phone)
    return wavepay_qr_string(phone)


@router.message(F.text)
async def phone_to_qr(
    message: Message, state: FSMContext, provider: Provider | None
) -> None:
    if provider is None:
        await message.reply(texts.NO_PROVIDER, reply_markup=provider_keyboard())
        return

    # Keep FSM state in sync so the next update skips the database lookup.
    await state.update_data(provider=provider.value)

    check = validate(message.text or "", provider)
    if not check.ok:
        await message.reply(
            texts.phone_error(check),
            reply_markup=provider_keyboard(active=provider),
        )
        return

    phone = check.phone
    warning = texts.PADDING_WARNING if needs_padding_warning(provider, phone) else None
    caption = texts.QR_CAPTION.format(label=PROVIDER_LABELS[provider], phone=phone)
    keyboard = provider_keyboard(active=provider)

    cached = cache.get(provider, phone, warning)
    if cached is not None:
        try:
            await message.reply_photo(cached, caption=caption, reply_markup=keyboard)
            return
        except TelegramBadRequest:
            # A file_id Telegram no longer accepts. Drop it and render afresh.
            logger.warning("stale file_id for %s (%s)", phone, provider.value)
            cache.discard(provider, phone, warning)

    payload = build_payload(provider, phone)
    png = await render_qr_card_async(provider, phone, payload, warning=warning)
    logger.info(
        "user %s: QR for %s (%s)",
        message.from_user.id if message.from_user else "unknown",
        phone,
        provider.value,
    )

    sent = await message.reply_photo(
        BufferedInputFile(png, filename=f"{provider.value}_{phone}.png"),
        caption=caption,
        reply_markup=keyboard,
    )
    if sent.photo:
        cache.put(provider, phone, sent.photo[-1].file_id, warning)


@router.message()
async def not_text(message: Message, provider: Provider | None) -> None:
    if provider is None:
        await message.reply(texts.NO_PROVIDER, reply_markup=provider_keyboard())
        return

    await message.reply(texts.NOT_TEXT, reply_markup=provider_keyboard(active=provider))
