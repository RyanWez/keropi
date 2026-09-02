import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, Message

from bot import texts
from bot.keyboards.provider_kb import provider_keyboard
from bot.services.kbzpay_qr import kbzpay_qr_string
from bot.services.providers import Provider
from bot.services.renderer import render_qr_card
from bot.services.validators import PROVIDER_LABELS, needs_padding_warning, validate
from bot.services.wavepay_qr import wavepay_qr_string

logger = logging.getLogger(__name__)
router = Router()


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
    payload = build_payload(provider, phone)
    warning = texts.PADDING_WARNING if needs_padding_warning(provider, phone) else None
    png = render_qr_card(provider, phone, payload, warning=warning)
    logger.info(
        "user %s: QR for %s (%s)",
        message.from_user.id if message.from_user else "unknown",
        phone,
        provider.value,
    )

    await message.reply_photo(
        BufferedInputFile(png, filename=f"{provider.value}_{phone}.png"),
        caption=texts.QR_CAPTION.format(label=PROVIDER_LABELS[provider], phone=phone),
        reply_markup=provider_keyboard(active=provider),
    )


@router.message()
async def not_text(message: Message, provider: Provider | None) -> None:
    if provider is None:
        await message.reply(texts.NO_PROVIDER, reply_markup=provider_keyboard())
        return

    await message.reply(texts.NOT_TEXT, reply_markup=provider_keyboard(active=provider))
