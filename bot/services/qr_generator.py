"""Transport-neutral QR preparation and rendering.

Telegram handlers and the web app both use this module so validation, payload
construction, warnings, and card output cannot drift between interfaces.
"""

from dataclasses import dataclass

from bot import texts
from bot.services.kbzpay_qr import kbzpay_qr_string
from bot.services.languages import Language
from bot.services.providers import Provider
from bot.services.renderer import render_qr_card_async
from bot.services.validators import (
    AmountCheck,
    PhoneCheck,
    needs_padding_warning,
    validate,
    validate_amount,
)
from bot.services.wavepay_qr import wavepay_qr_string


class PhoneValidationError(ValueError):
    def __init__(self, check: PhoneCheck) -> None:
        super().__init__(check.reason.value if check.reason else "invalid_phone")
        self.check = check


class AmountValidationError(ValueError):
    def __init__(self, check: AmountCheck) -> None:
        super().__init__(check.reason.value if check.reason else "invalid_amount")
        self.check = check


@dataclass(frozen=True, slots=True)
class PreparedQr:
    provider: Provider
    phone: str
    payload: str
    amount: int | None = None
    warning: str | None = None

    @property
    def filename(self) -> str:
        return f"{self.provider.value}_{self.phone}.png"


def build_payload(provider: Provider, phone: str, amount: int | None = None) -> str:
    if provider is Provider.KBZPAY:
        return kbzpay_qr_string(phone, amount=amount)
    return wavepay_qr_string(phone)


def prepare_qr(
    provider: Provider,
    raw_phone: str,
    language: Language,
    raw_amount: str | None = None,
) -> PreparedQr:
    check = validate(raw_phone, provider)
    if not check.ok:
        raise PhoneValidationError(check)

    amount_check = validate_amount(raw_amount, provider)
    if not amount_check.ok:
        raise AmountValidationError(amount_check)

    phone = check.phone
    warning = (
        texts.get(language).PADDING_WARNING
        if needs_padding_warning(provider, phone)
        else None
    )
    return PreparedQr(
        provider=provider,
        phone=phone,
        payload=build_payload(provider, phone, amount_check.amount),
        amount=amount_check.amount,
        warning=warning,
    )


async def render_prepared_qr(prepared: PreparedQr) -> bytes:
    return await render_qr_card_async(
        prepared.provider,
        prepared.phone,
        prepared.payload,
        warning=prepared.warning,
        amount=prepared.amount,
    )
