from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.services.providers import Provider

CALLBACK_PREFIX = "provider:"

LABELS = {Provider.KBZPAY: "KBZ Pay", Provider.WAVEPAY: "WavePay"}


def provider_keyboard(active: Provider | None = None) -> InlineKeyboardMarkup:
    """Two inline buttons shown under every message; the active provider gets a check mark."""
    builder = InlineKeyboardBuilder()
    for provider in (Provider.KBZPAY, Provider.WAVEPAY):
        label = LABELS[provider]
        if provider is active:
            label = f"✅ {label}"
        builder.button(text=label, callback_data=f"{CALLBACK_PREFIX}{provider.value}")
    builder.adjust(2)
    return builder.as_markup()
