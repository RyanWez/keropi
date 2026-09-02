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


def _create(conn: sqlite3.Connection) -> None:
    # Both preference columns are nullable: a user may set a language without ever
    # having picked a provider, and vice versa.
    conn.execute("CREATE TABLE IF NOT EXISTS user_settings (user_id INTEGER PRIMARY KEY, provider TEXT, lang TEXT, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")


def _not_null_columns(conn: sqlite3.Connection) -> dict[str, bool]:
    """Column name -> whether it carries a NOT NULL constraint."""
    rows = conn.execute("PRAGMA table_info(user_settings)")
    return {row[1]: bool(row[3]) for row in rows}


def _migrate(conn: sqlite3.Connection) -> None:
    """Bring a pre-existing table up to the current shape.

    Two earlier shapes exist: one without a `lang` column, and one where `provider`
    was NOT NULL, which blocks storing a language for a user who has not picked a
    provider. SQLite cannot drop a NOT NULL constraint in place, so that one is
    rebuilt and copied across.
    """
    columns = _not_null_columns(conn)
    if not columns:
        return

    if "lang" not in columns:
        conn.execute("ALTER TABLE user_settings ADD COLUMN lang TEXT")
        columns = _not_null_columns(conn)

    if columns.get("provider"):
        logger.info("rebuilding user_settings to allow a null provider")
        conn.execute("ALTER TABLE user_settings RENAME TO user_settings_old")
        _create(conn)
        conn.execute("INSERT INTO user_settings (user_id, provider, lang, updated_at) SELECT user_id, provider, lang, updated_at FROM user_settings_old")
        conn.execute("DROP TABLE user_settings_old")


def _ensure_schema() -> None:
    """Create or migrate on first use.

    Import-time side effects are avoided so that tests, and anything that merely
    imports the package, don't leave a stray database file behind.
    """
    global _initialised

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(DB_PATH, timeout=5.0)) as conn:
        # WAL lets reads proceed while a write is in flight, which matters once
        # several updates are handled concurrently.
        conn.execute("PRAGMA journal_mode=WAL")
        _migrate(conn)
        _create(conn)
        conn.commit()
    _initialised = DB_PATH


def _connect() -> sqlite3.Connection:
    if _initialised != DB_PATH:
        _ensure_schema()
    return sqlite3.connect(DB_PATH, timeout=5.0)


def get_user_settings(user_id: int) -> tuple[str | None, str | None]:
    """Return (provider, lang). One query, because both are needed per update."""
    try:
        with closing(_connect()) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT provider, lang FROM user_settings WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            return (row[0], row[1]) if row else (None, None)
    except Exception:
        logger.warning("could not read settings for user %s", user_id, exc_info=True)
        return None, None


def get_user_provider(user_id: int) -> str | None:
    return get_user_settings(user_id)[0]


def get_user_lang(user_id: int) -> str | None:
    return get_user_settings(user_id)[1]


def set_user_provider(user_id: int, provider: str) -> None:
    """Save the selected provider, leaving any stored language untouched."""
    try:
        with closing(_connect()) as conn:
            # Ensure the row, then set one column: user_id is the primary key and
            # every preference column is nullable, so this never disturbs the other.
            conn.execute("INSERT OR IGNORE INTO user_settings (user_id) VALUES (?)", (user_id,))
            conn.execute("UPDATE user_settings SET provider = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?", (provider, user_id))
            conn.commit()
    except Exception:
        logger.warning("could not save provider for user %s", user_id, exc_info=True)


def set_user_lang(user_id: int, lang: str) -> None:
    """Save the selected language, leaving any stored provider untouched."""
    try:
        with closing(_connect()) as conn:
            conn.execute("INSERT OR IGNORE INTO user_settings (user_id) VALUES (?)", (user_id,))
            conn.execute("UPDATE user_settings SET lang = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?", (lang, user_id))
            conn.commit()
    except Exception:
        logger.warning("could not save lang for user %s", user_id, exc_info=True)
