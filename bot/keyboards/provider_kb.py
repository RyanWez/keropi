from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot import config
from bot.services.providers import Provider

CALLBACK_PREFIX = "provider:"

LABELS = {Provider.KBZPAY: "KBZ Pay", Provider.WAVEPAY: "WavePay"}

CONTACT_LABEL = "💬 Contact & Feedback"


def _add_providers(builder: InlineKeyboardBuilder, active: Provider | None) -> None:
    for provider in (Provider.KBZPAY, Provider.WAVEPAY):
        label = LABELS[provider]
        if provider is active:
            label = f"✅ {label}"
        builder.button(text=label, callback_data=f"{CALLBACK_PREFIX}{provider.value}")


def provider_keyboard(active: Provider | None = None) -> InlineKeyboardMarkup:
    """Two inline buttons shown under every message; the active provider gets a check mark."""
    builder = InlineKeyboardBuilder()
    _add_providers(builder, active)
    builder.adjust(2)
    return builder.as_markup()


def error_keyboard(
    active: Provider | None = None, *, offer_providers: bool = False
) -> InlineKeyboardMarkup:
    """Keyboard for a failed request: reach a human instead of the provider switch.

    ``offer_providers`` keeps the provider row above the contact button, for the one
    error whose own text tells the user to tap a provider — refusing a short number
    for KBZ Pay and pointing at WavePay. Everywhere else switching provider is not
    the remedy, so only the contact button is shown.
    """
    if config.CONTACT_URL is None:
        return provider_keyboard(active)

    builder = InlineKeyboardBuilder()
    if offer_providers:
        _add_providers(builder, active)
        builder.button(text=CONTACT_LABEL, url=config.CONTACT_URL)
        builder.adjust(2, 1)
    else:
        builder.button(text=CONTACT_LABEL, url=config.CONTACT_URL)
        builder.adjust(1)
    return builder.as_markup()