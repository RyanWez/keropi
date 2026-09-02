import logging
import os
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv

load_dotenv()


def _flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    try:
        return int(raw) if raw else default
    except ValueError:
        return default


BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN is not set. Copy .env.example to .env and paste your token from @BotFather."
    )

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Health-check server for platforms that require an open port (Render). 0 disables it.
PORT = _int("PORT", 0)

# Telegram user id allowed to run diagnostic commands. 0 disables them entirely.
OWNER_ID = _int("OWNER_ID", 0)

# KBZPay encodes the recipient's number into a fixed 6-byte BCD field, which holds
# exactly 11 digits plus one 0xD pad nibble. Myanmar also has legacy 9- and 10-digit
# mobile numbers; padding those to fill the field is plausible but UNVERIFIED, because
# the 42-byte payload is built by KBZPay's server, not by the app, so there is no
# client-side encoder to copy the padding rule from. Leave this off until a real
# legacy-number Receive QR has been decoded and the rule confirmed.
KBZPAY_ALLOW_SHORT_NUMBERS = _flag("KBZPAY_ALLOW_SHORT_NUMBERS", default=False)


def setup_logging() -> None:
    fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
    root = logging.getLogger()
    root.setLevel(LOG_LEVEL)

    # Suppress verbose framework chatter (Update id=... duration ms)
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    # Automatically rotates when log reaches 1MB, keeps maximum 3 backup files (Total max ~4MB)
    file_handler = RotatingFileHandler(
        "bot.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)
