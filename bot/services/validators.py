import re

from bot.services.providers import Provider

# 09 + 8 or 9 digits covers current Myanmar mobile numbers;
# 10-digit (old MPT) is accepted but flagged in the reply caption.
_PHONE_RE = re.compile(r"^09\d{8,9}$")


def normalize(raw: str) -> str:
    return re.sub(r"[\s\-()+]", "", raw.strip())


def validate(raw: str) -> tuple[str | None, str | None]:
    """Return (phone, error). Exactly one of the two is not None."""
    phone = normalize(raw)
    if not phone.isdigit():
        return None, "Numbers only, please. Example: 09960476738"
    if phone.startswith("+95") or phone.startswith("95"):
        return None, "Drop the country code — start with 09."
    if not phone.startswith("09"):
        return None, "Myanmar mobile numbers start with 09. Example: 09960476738"
    if not _PHONE_RE.match(phone):
        return None, "That does not look right. Use 09 followed by 8–9 digits (10–11 digits total)."
    return phone, None


def is_legacy_short(phone: str) -> bool:
    """Old MPT 10-digit numbers produce a payload variant the KBZPay server has not been tested against."""
    return len(phone) == 10


PROVIDER_LABELS = {Provider.KBZPAY: "KBZ Pay", Provider.WAVEPAY: "WavePay"}
