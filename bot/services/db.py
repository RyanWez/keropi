import sqlite3
from pathlib import Path

DB_PATH = Path("bot.db")


def _init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
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


_init_db()


def get_user_provider(user_id: int) -> str | None:
    """Retrieve saved provider for a user."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT provider FROM user_settings WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            return row[0] if row else None
    except Exception:
        return None


def set_user_provider(user_id: int, provider: str) -> None:
    """Save or update selected provider for a user."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
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
        pass
