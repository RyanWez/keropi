import logging

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, Message

from bot import texts
from bot.keyboards import error_keyboard, provider_keyboard
from bot.services.languages import Language
from bot.services.providers import Provider
from bot.services.qr_cache import cache
from bot.services.qr_generator import (
    PhoneValidationError,
    prepare_qr,
    render_prepared_qr,
)
from bot.services.validators import PROVIDER_LABELS

logger = logging.getLogger(__name__)
router = Router(name="phone")

# These two handlers are catch-alls. In a group with privacy mode off they would
# answer every message posted, so keep them to one-to-one chats; the commands in
# start.py still work anywhere.
router.message.filter(F.chat.type == ChatType.PRIVATE)


@router.message(F.text)
async def phone_to_qr(
    message: Message, state: FSMContext, provider: Provider | None, lang: Language
) -> None:
    strings = texts.get(lang)
    if provider is None:
        await message.reply(strings.NO_PROVIDER, reply_markup=provider_keyboard())
        return

    # Keep FSM state in sync so the next update skips the database lookup.
    await state.update_data(provider=provider.value, lang=lang.value)

    try:
        prepared = prepare_qr(provider, message.text or "", lang)
    except PhoneValidationError as exc:
        await message.reply(
            strings.phone_error(exc.check),
            reply_markup=error_keyboard(
                strings.CONTACT_LABEL,
                provider,
                offer_providers=texts.offers_provider_switch(exc.check),
            ),
        )
        return

    phone = prepared.phone
    caption = strings.QR_CAPTION.format(label=PROVIDER_LABELS[provider], phone=phone)
    keyboard = provider_keyboard(active=provider)

    cached = cache.get(provider, phone, prepared.warning)
    if cached is not None:
        try:
            await message.reply_photo(cached, caption=caption, reply_markup=keyboard)
            return
        except TelegramBadRequest:
            # A file_id Telegram no longer accepts. Drop it and render afresh.
            logger.warning("stale file_id for %s (%s)", phone, provider.value)
            cache.discard(provider, phone, prepared.warning)

    png = await render_prepared_qr(prepared)
    logger.info(
        "user %s: QR for %s (%s)",
        message.from_user.id if message.from_user else "unknown",
        phone,
        provider.value,
    )

    sent = await message.reply_photo(
        BufferedInputFile(png, filename=prepared.filename),
        caption=caption,
        reply_markup=keyboard,
    )
    if sent.photo:
        cache.put(provider, phone, sent.photo[-1].file_id, prepared.warning)


@router.message()
async def not_text(message: Message, provider: Provider | None, lang: Language) -> None:
    strings = texts.get(lang)
    if provider is None:
        await message.reply(strings.NO_PROVIDER, reply_markup=provider_keyboard())
        return

    await message.reply(
        strings.NOT_TEXT,
        reply_markup=error_keyboard(strings.CONTACT_LABEL, provider),
    )
