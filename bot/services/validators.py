import re

from bot.services.providers import Provider


def normalize(raw: str) -> str:
    """Remove spaces, hyphens, parentheses, and plus signs."""
    return re.sub(r"[\s\-()+]", "", raw.strip())


def validate(raw: str) -> tuple[str | None, str | None]:
    """Return (phone, error). Exactly one of the two is not None.
    
    Accepts numbers only with length between 5 and 11 digits.
    """
    cleaned = raw.strip()
    if not cleaned:
        return None, "Please enter a valid phone number (5 to 11 digits)."

    phone = normalize(raw)

    # 1. Strictly digits only
    if not phone.isdigit():
        return (
            None,
            "⚠️ Numbers only, please. Letters or special symbols are not allowed.\n"
            "Example: <code>09***6738</code>",
        )

    # 2. Auto-normalize international Myanmar prefix (e.g. +959... -> 09...)
    if phone.startswith("959") and len(phone) in (11, 12, 13):
        phone = "0" + phone[2:]
    elif phone.startswith("95") and len(phone) > 10:
        phone = "0" + phone[2:]

    # 3. Digit length check (minimum 7 to maximum 11 digits)
    if len(phone) < 7:
        return (
            None,
            f"⚠️ Number is too short ({len(phone)} digits). Please enter between 7 and 11 digits.",
        )
    if len(phone) > 11:
        return (
            None,
            f"⚠️ Number is too long ({len(phone)} digits). Please enter between 7 and 11 digits.",
        )

    return phone, None


def is_legacy_short(phone: str) -> bool:
    """Old numbers or short numbers that might require user verification."""
    return len(phone) <= 10


PROVIDER_LABELS = {Provider.KBZPAY: "KBZ Pay", Provider.WAVEPAY: "WavePay"}
