import os
import logging
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN is not set. Copy .env.example to .env and paste your token from @BotFather."
    )

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


def setup_logging() -> None:
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
    )
    root = logging.getLogger()
    root.setLevel(LOG_LEVEL)

    # Suppress verbose framework chatter (Update id=... duration ms)
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    # Automatically rotates when log reaches 1MB, keeps maximum 3 backup files (Total max ~3MB)
    file_handler = RotatingFileHandler(
        "bot.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)
