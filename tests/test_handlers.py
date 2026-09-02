"""Drives the real dispatcher with fake updates.

The unit tests cover encoding and validation; this checks the parts that only
break once handlers, middlewares and the error observer are wired together.

All numbers here are synthetic.
"""

import asyncio
from datetime import datetime, timezone

import pytest
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.methods import SendMessage, SendPhoto
from aiogram.types import Chat, Message, Update, User

from bot.handlers import setup
from bot.services.providers import Provider

CHAT_ID = 5_000_001
USER_ID = 5_000_002


class RecordingBot:
    """Stands in for Bot: records calls instead of talking to Telegram."""

    id = 999
    session = None

    def __init__(self) -> None:
        self.calls: list[object] = []

    async def __call__(self, method, request_timeout=None):  # noqa: ANN001, ARG002
        self.calls.append(method)
        return True

    @property
    def sent_texts(self) -> list[str]:
        return [c.text for c in self.calls if isinstance(c, SendMessage)]

    @property
    def sent_photos(self) -> list[SendPhoto]:
        return [c for c in self.calls if isinstance(c, SendPhoto)]


def _update(text: str, message_id: int = 1) -> Update:
    return Update(
        update_id=message_id,
        message=Message(
            message_id=message_id,
            date=datetime.now(timezone.utc),
            chat=Chat(id=CHAT_ID, type="private"),
            from_user=User(id=USER_ID, is_bot=False, first_name="Tester"),
            text=text,
        ),
    )


@pytest.fixture(scope="module")
def dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(setup())
    return dp


@pytest.fixture(autouse=True)
def _isolate(dispatcher, tmp_path, monkeypatch):
    """Fresh FSM per test, and no stored provider unless a test asks for one."""
    dispatcher.fsm.storage = MemoryStorage()
    monkeypatch.setattr("bot.services.db.DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr("bot.services.db._initialised", None)
    monkeypatch.setattr(
        "bot.middlewares.provider_ctx.get_user_provider", lambda _uid: None
    )


@pytest.fixture
def bot() -> RecordingBot:
    return RecordingBot()


def _select(monkeypatch, provider: Provider) -> None:
    monkeypatch.setattr(
        "bot.middlewares.provider_ctx.get_user_provider", lambda _uid: provider.value
    )


def _feed(dp: Dispatcher, bot: RecordingBot, text: str) -> None:
    asyncio.run(dp.feed_update(bot, _update(text)))


def test_start_offers_both_providers(dispatcher, bot):
    _feed(dispatcher, bot, "/start")

    (sent,) = bot.calls
    assert isinstance(sent, SendMessage)
    labels = [b.text for row in sent.reply_markup.inline_keyboard for b in row]
    assert labels == ["KBZ Pay", "WavePay"]


def test_number_without_a_provider_asks_for_one(dispatcher, bot):
    _feed(dispatcher, bot, "09123456789")
    assert "choose a provider" in bot.sent_texts[0].lower()
    assert not bot.sent_photos


def test_kbzpay_11_digits_returns_a_photo(dispatcher, bot, monkeypatch):
    _select(monkeypatch, Provider.KBZPAY)
    _feed(dispatcher, bot, "+95 9 123 456 789")

    (photo,) = bot.sent_photos
    assert "09123456789" in photo.caption
    assert "KBZ Pay" in photo.caption
    assert photo.photo.filename == "kbzpay_09123456789.png"


def test_kbzpay_10_digits_explains_instead_of_guessing(dispatcher, bot, monkeypatch):
    _select(monkeypatch, Provider.KBZPAY)
    _feed(dispatcher, bot, "0912345678")

    assert not bot.sent_photos, "must not emit a QR built on unverified padding"
    reply = bot.sent_texts[0]
    assert "11-digit" in reply
    assert "10 digits" in reply
    assert "WavePay" in reply


def test_wavepay_accepts_a_10_digit_number(dispatcher, bot, monkeypatch):
    _select(monkeypatch, Provider.WAVEPAY)
    _feed(dispatcher, bot, "0912345678")

    (photo,) = bot.sent_photos
    assert "0912345678" in photo.caption


def test_unicode_digits_get_a_reply_rather_than_a_crash(dispatcher, bot, monkeypatch):
    _select(monkeypatch, Provider.KBZPAY)
    _feed(dispatcher, bot, "09960476\u00b2\u00b23")

    assert not bot.sent_photos
    assert "Numbers only" in bot.sent_texts[0]


def test_a_corrupt_stored_provider_does_not_break_start(dispatcher, bot, monkeypatch):
    monkeypatch.setattr(
        "bot.middlewares.provider_ctx.get_user_provider", lambda _uid: "moneygram"
    )
    _feed(dispatcher, bot, "/start")
    assert bot.sent_texts, "/start must still answer"


def test_the_error_handler_replies_when_a_handler_explodes(
    dispatcher, bot, monkeypatch
):
    _select(monkeypatch, Provider.KBZPAY)

    def boom(*_args, **_kwargs):
        raise RuntimeError("renderer exploded")

    monkeypatch.setattr("bot.handlers.phone.render_qr_card", boom)
    _feed(dispatcher, bot, "09123456789")

    assert not bot.sent_photos
    assert "went wrong" in bot.sent_texts[-1]


def test_help_lists_the_kbzpay_length_rule(dispatcher, bot):
    _feed(dispatcher, bot, "/help")
    assert "11-digit" in bot.sent_texts[0]
