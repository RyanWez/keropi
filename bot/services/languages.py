"""Which language the bot replies in."""

from enum import Enum


class Language(str, Enum):
    EN = "en"
    MY = "my"


DEFAULT_LANGUAGE = Language.EN

#: Shown on the language buttons. Endonyms, so they read the same either way and a
#: user who picked the wrong one can still find their way back.
LANGUAGE_NAMES = {Language.EN: "English", Language.MY: "မြန်မာ"}


def parse_language(value: str | None) -> Language | None:
    """Tolerant lookup for a value from storage or a callback payload."""
    if not value:
        return None
    try:
        return Language(value)
    except ValueError:
        return None


def from_telegram(language_code: str | None) -> Language:
    """Guess from the user's Telegram client language, for a first-time user.

    Telegram sends an IETF tag such as "my" or "en-GB", so only the primary
    subtag is meaningful here.
    """
    if not language_code:
        return DEFAULT_LANGUAGE
    return parse_language(language_code.split("-")[0].lower()) or DEFAULT_LANGUAGE
