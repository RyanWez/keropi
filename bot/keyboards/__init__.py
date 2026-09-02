"""Inline keyboards.

Provider names are brands, so they read the same in every language; only the
contact button's label is translated. The language buttons use endonyms, so a user
who picked the wrong language can still find their way back.
"""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot import config
from bot.services.languages import LANGUAGE_NAMES, Language
from bot.services.providers import Provider

PROVIDER_PREFIX = "provider:"
LANG_PREFIX = "lang:"

LABELS = {Provider.KBZPAY: "KBZ Pay", Provider.WAVEPAY: "WavePay"}


def _tick(label: str, selected: bool) -> str:
    return f"✅ {label}" if selected else label


def _add_providers(builder: InlineKeyboardBuilder, active: Provider | None) -> None:
    for provider in (Provider.KBZPAY, Provider.WAVEPAY):
        builder.button(
            text=_tick(LABELS[provider], provider is active),
            callback_data=f"{PROVIDER_PREFIX}{provider.value}",
        )


def provider_keyboard(active: Provider | None = None) -> InlineKeyboardMarkup:
    """Two inline buttons shown under every message; the active one gets a check mark."""
    builder = InlineKeyboardBuilder()
    _add_providers(builder, active)
    builder.adjust(2)
    return builder.as_markup()


def language_keyboard(active: Language | None = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for language in (Language.EN, Language.MY):
        builder.button(
            text=_tick(LANGUAGE_NAMES[language], language is active),
            callback_data=f"{LANG_PREFIX}{language.value}",
        )
    builder.adjust(2)
    return builder.as_markup()


def error_keyboard(
    contact_label: str,
    active: Provider | None = None,
    *,
    offer_providers: bool = False,
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
        builder.button(text=contact_label, url=config.CONTACT_URL)
        builder.adjust(2, 1)
    else:
        builder.button(text=contact_label, url=config.CONTACT_URL)
        builder.adjust(1)
    return builder.as_markup()
