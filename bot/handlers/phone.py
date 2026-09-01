import logging

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, Message

from bot import texts
from bot.keyboards.provider_kb import provider_keyboard
from bot.services.kbzpay_qr import kbzpay_qr_string
from bot.services.providers import Provider
from bot.services.renderer import render_qr_card
from bot.services.validators import PROVIDER_LABELS, is_legacy_short, validate
from bot.services.wavepay_qr import wavepay_qr_string
from bot.states import QrFlow

logger = logging.getLogger(__name__)
router = Router()


def build_payload(provider: Provider, phone: str) -> str:
    if provider is Provider.KBZPAY:
        return kbzpay_qr_string(phone)
    return wavepay_qr_string(phone)


@router.message(StateFilter(QrFlow.waiting_phone), F.text)
async def phone_to_qr(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    provider_value = data.get("provider")
    if provider_value is None:
        await message.reply(texts.NO_PROVIDER, reply_markup=provider_keyboard())
        return

    phone, error = validate(message.text or "")
    if error is not None:
        await message.reply(error, reply_markup=provider_keyboard())
        return

    provider = Provider(provider_value)
    payload = build_payload(provider, phone)
    warning = texts.LEGACY_WARNING if is_legacy_short(phone) else None
    png = render_qr_card(provider, phone, payload, warning=warning)
    logger.info("chat %s: QR for %s (%s)", message.chat.id, phone, provider.value)

    await message.reply_photo(
        BufferedInputFile(png, filename=f"{provider.value}_{phone}.png"),
        caption=texts.QR_CAPTION.format(label=PROVIDER_LABELS[provider], phone=phone),
        reply_markup=provider_keyboard(active=provider),
    )


@router.message(StateFilter(QrFlow.waiting_phone))
async def not_text(message: Message) -> None:
    await message.reply(
        "Please send the phone number as text (e.g. <code>09***6738</code>).",
        reply_markup=provider_keyboard(),
    )
