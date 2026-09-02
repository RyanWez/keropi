import ipaddress
import logging
import os
from logging.handlers import RotatingFileHandler
from urllib.parse import urlsplit

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


def _button_url(name: str, default: str = "") -> str | None:
    """Validate a URL destined for an inline button, or return None.

    Telegram rejects the whole message if a button URL is malformed, and the
    messages carrying this one are error replies — the last place that should fail.
    So a bad value disables the button rather than breaking the reply.
    """
    raw = os.getenv(name)
    # An explicitly empty value means "no button"; only an unset one takes the default.
    raw = (default if raw is None else raw).strip()
    if not raw:
        return None

    parsed = urlsplit(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        logging.getLogger(__name__).warning(
            "%s must be an http(s) URL with a host; ignoring %r", name, raw
        )
        return None

    host = parsed.hostname.lower()
    if host == "localhost" or host.endswith(".localhost"):
        return None
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        pass  # a domain name, which is what we expect
    else:
        if not address.is_global:
            logging.getLogger(__name__).warning(
                "%s points at a non-routable address; ignoring %r", name, raw
            )
            return None
    return raw


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

# Card rendering is CPU work (Pillow, roughly 30 ms and ~10 MB peak per card), so it
# runs in a small thread pool rather than on the event loop. Keep this low: Render's
# free instance has 512 MB and an unpublished CPU share, and asyncio.to_thread's
# default pool would open dozens of workers.
RENDER_WORKERS = _int("RENDER_WORKERS", 3)

# Ceiling on updates processed at once. aiogram acquires this semaphore inside the
# polling loop, so hitting the limit slows getUpdates instead of queueing tasks in
# memory.
MAX_CONCURRENT_UPDATES = _int("MAX_CONCURRENT_UPDATES", 24)

# Per-user cooldown in seconds. Telegram allows a bot about 30 messages per second
# overall, and a 429 stalls the bot for *everyone*, so this exists to stop one
# user's burst from degrading the service rather than to keep anybody out.
THROTTLE_SECONDS = float(os.getenv("THROTTLE_SECONDS", "2") or 2)

# How many rendered cards to remember as Telegram file_ids, so a repeat number is
# answered without rendering or uploading again.
QR_CACHE_SIZE = _int("QR_CACHE_SIZE", 2000)

# Inline results can only reference a URL or a file_id — raw bytes are not accepted —
# so a card must be uploaded somewhere before it can be offered inline. Point this at
# a private channel or group the bot can post to. Unset disables inline mode, which
# then falls back to a "open the bot" button.
QR_CACHE_CHAT_ID = _int("QR_CACHE_CHAT_ID", 0)

# Where the "Contact & Feedback" button on error replies points. When something has
# gone wrong is exactly when someone wants to reach a human, and the provider
# buttons are no use to them. Set to empty to drop the button.
CONTACT_URL = _button_url("CONTACT_URL", "https://t.me/Super001z")


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
