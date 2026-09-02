from enum import Enum


class Provider(str, Enum):
    KBZPAY = "kbzpay"
    WAVEPAY = "wavepay"


def parse_provider(value: str | None) -> Provider | None:
    """Tolerant lookup for values that came from storage or a callback payload.

    Returns None instead of raising so a stale or renamed value can't break /start.
    """
    if not value:
        return None
    try:
        return Provider(value)
    except ValueError:
        return None
