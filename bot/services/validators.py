"""Myanmar mobile number normalisation and validation.

Length rules come from the Posts and Telecommunications Department's
Telecommunications Numbering Plan (2017): the mobile NDC is 9 and subscriber
numbers are 7, 8 or 9 digits, so a national number starting "09" is 9, 10 or 11
digits long. Numbers shorter than that are landlines, not mobiles. Since 2014
every newly issued mobile number is 11 digits, but the older 9- and 10-digit
ranges were never withdrawn and are still in service.

Errors are returned as reason codes rather than prose so that the wording lives
in ``bot.texts`` and can be translated later.
"""

import re
from dataclasses import dataclass
from enum import Enum

from bot import config
from bot.services.providers import Provider

#: A national-format Myanmar mobile number: "09" followed by 7, 8 or 9 digits.
MOBILE_RE = re.compile(r"09\d{7,9}")

#: Total digit counts that MOBILE_RE accepts, for building error messages.
VALID_LENGTHS = (9, 10, 11)

#: KBZPay's BCD field holds exactly this many digits.
KBZPAY_REQUIRED_LENGTH = 11

_SEPARATORS_RE = re.compile(r"[\s\-()./]+")
_ASCII_DIGITS_RE = re.compile(r"[0-9]+")

PROVIDER_LABELS = {Provider.KBZPAY: "KBZ Pay", Provider.WAVEPAY: "WavePay"}


class Reason(str, Enum):
    EMPTY = "empty"
    NOT_DIGITS = "not_digits"
    NOT_MYANMAR_MOBILE = "not_myanmar_mobile"
    KBZPAY_NEEDS_11 = "kbzpay_needs_11"


@dataclass(frozen=True, slots=True)
class PhoneCheck:
    """Either ``phone`` is set, or ``reason`` is."""

    phone: str | None = None
    reason: Reason | None = None
    #: Digit count of the normalised candidate, for "you sent N digits" messages.
    digits: int = 0

    @property
    def ok(self) -> bool:
        return self.phone is not None


def strip_separators(raw: str) -> str:
    """Drop the punctuation people type inside phone numbers."""
    return _SEPARATORS_RE.sub("", raw.strip())


def normalize(raw: str) -> str | None:
    """Return a national-format ``09…`` number, or None if the input cannot be one.

    Handles the international forms ``+959…``, ``00959…``, ``959…`` and ``9509…``,
    and supplies a missing trunk zero. An explicit ``+`` or ``00`` is treated as a
    country-code marker; without one, a leading ``9`` is read as a dropped trunk
    zero. That distinction matters: ``9591234567`` is otherwise ambiguous between
    ``09591234567`` and ``091234567``, and honouring the user's own prefix avoids
    guessing which account they meant.
    """
    text = raw.strip()
    explicit_international = text.startswith("+")

    digits = strip_separators(text.lstrip("+"))
    if not digits or not _ASCII_DIGITS_RE.fullmatch(digits):
        return None

    if digits.startswith("00"):
        explicit_international = True
        digits = digits[2:]

    candidates: list[str] = []
    if explicit_international:
        if digits.startswith("95"):
            rest = digits[2:]
            candidates.append(rest if rest.startswith("0") else "0" + rest)
        candidates.append(digits)
    else:
        candidates.append(digits)
        if digits.startswith("9") and not digits.startswith("09"):
            candidates.append("0" + digits)
        if digits.startswith("95"):
            rest = digits[2:]
            candidates.append(rest if rest.startswith("0") else "0" + rest)

    for candidate in candidates:
        if MOBILE_RE.fullmatch(candidate):
            return candidate
    return None


def validate(raw: str, provider: Provider) -> PhoneCheck:
    """Normalise ``raw`` and check it against the provider's own constraints."""
    if not raw or not raw.strip():
        return PhoneCheck(reason=Reason.EMPTY)

    digits = strip_separators(raw.lstrip("+").strip())
    if not digits:
        return PhoneCheck(reason=Reason.EMPTY)

    # ``str.isdigit()`` is true for Unicode digits such as "²" and "٩", which then
    # blow up inside the BCD encoder. Only ASCII 0-9 may pass.
    if not _ASCII_DIGITS_RE.fullmatch(digits):
        return PhoneCheck(reason=Reason.NOT_DIGITS)

    phone = normalize(raw)
    if phone is None:
        return PhoneCheck(reason=Reason.NOT_MYANMAR_MOBILE, digits=len(digits))

    if provider is Provider.KBZPAY and len(phone) != KBZPAY_REQUIRED_LENGTH:
        # Read through the module so tests and a restart-free config change both work.
        if not config.KBZPAY_ALLOW_SHORT_NUMBERS:
            return PhoneCheck(reason=Reason.KBZPAY_NEEDS_11, digits=len(phone))

    return PhoneCheck(phone=phone, digits=len(phone))


def needs_padding_warning(provider: Provider, phone: str) -> bool:
    """True when the QR relies on the unverified short-number padding."""
    return provider is Provider.KBZPAY and len(phone) != KBZPAY_REQUIRED_LENGTH
