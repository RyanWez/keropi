"""Per-user settings.

Deliberately tiny and failure-tolerant: everything here is a convenience. Losing
it costs the user one button tap, so a storage error must never take down a QR
request.

Note for Render's free tier: the filesystem is ephemeral, so this file is wiped on
every redeploy, restart and spin-down. That is fine for preferences. Point DB_PATH
at a mounted disk, or swap this module for a hosted database, if durability starts
to matter.

Every statement here is a fixed literal using ? placeholders; no value is ever
formatted or concatenated into the SQL.
"""

import logging
import os
import sqlite3
from contextlib import closing
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path(os.getenv("DB_PATH", "bot.db"))

_initialised: Path | None = None


def _ensure_schema() -> None:
    """Create the table on first use. Import-time side effects are avoided so that
    tests (and anything that merely imports the package) don't create a stray file."""
    global _initialised

    with closing(sqlite3.connect(DB_PATH, timeout=5.0)) as conn:
        # WAL lets reads proceed while a write is in flight, which matters once
        # several updates are handled concurrently.
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                provider TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
        # Databases created before `lang` existed need the column added; CREATE
        # TABLE IF NOT EXISTS is a no-op for them. Nothing reads it yet — it is
        # here so a later /lang switch needs no migration step.
        try:
            conn.execute("ALTER TABLE user_settings ADD COLUMN lang TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass
    _initialised = DB_PATH


def _connect() -> sqlite3.Connection:
    if _initialised != DB_PATH:
        _ensure_schema()
    return sqlite3.connect(DB_PATH, timeout=5.0)


def get_user_provider(user_id: int) -> str | None:
    """Retrieve saved provider for a user."""
    try:
        with closing(_connect()) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT provider FROM user_settings WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            return row[0] if row else None
    except Exception:
        logger.warning("could not read provider for user %s", user_id, exc_info=True)
        return None


def set_user_provider(user_id: int, provider: str) -> None:
    """Save or update selected provider for a user."""
    try:
        with closing(_connect()) as conn:
            conn.execute(
                """
                INSERT INTO user_settings (user_id, provider, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    provider = excluded.provider,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (user_id, provider),
            )
            conn.commit()
    except Exception:
        logger.warning("could not save provider for user %s", user_id, exc_info=True)
