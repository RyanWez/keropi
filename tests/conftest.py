"""Shared test setup.

``bot.config`` raises at import time when BOT_TOKEN is missing, so a dummy token is
installed before any bot module is imported.
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("BOT_TOKEN", "111111:test-token-not-real")
os.environ.setdefault("LOG_LEVEL", "WARNING")

import pytest  # noqa: E402
from aiogram import Dispatcher  # noqa: E402
from aiogram.fsm.storage.memory import MemoryStorage  # noqa: E402

from bot.handlers import setup  # noqa: E402
from bot.services.qr_cache import cache  # noqa: E402


@pytest.fixture(scope="session")
def dispatcher() -> Dispatcher:
    """The one and only dispatcher.

    aiogram routers are module-level singletons and a Router may have only one
    parent, so the handler tree can be attached to a single Dispatcher per process.
    Tests that need one share this.
    """
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(setup())
    return dp


@pytest.fixture(autouse=True)
def _clean_state(tmp_path, monkeypatch):
    """Point storage at a temporary file and empty the cache before every test.

    Autouse so no test can read or write the repository's own bot.db.
    """
    monkeypatch.setattr("bot.services.db.DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr("bot.services.db._initialised", None)
    cache._entries.clear()
