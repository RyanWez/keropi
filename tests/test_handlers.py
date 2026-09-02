"""Drives the real dispatcher with fake updates.

The unit tests cover encoding and validation; this checks the parts that only
break once handlers, middlewares and the error observer are wired together.

All numbers here are synthetic.
"""

import asyncio
from datetime import datetime, timezone

import pytest
from aiogram import Dispatcher
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.methods import AnswerInlineQuery, SendMessage, SendPhoto
from aiogram.types import BufferedInputFile, Chat, InlineQuery, Message, PhotoSize, Update, User

from bot.handlers import setup
from bot.services import renderer
from bot.services.kbzpay_qr import kbzpay_qr_string
from bot.services.providers import Provider
from bot.services.qr_cache import cache

CHAT_ID = 5_000_001
USER_ID = 5_000_002


class RecordingBot:
    """Stands in for Bot: records calls and returns plausible responses.

    Returning a real Message for sends matters — the handler reads
    ``sent.photo[-1].file_id`` to populate the file_id cache, and a stub that
    answered ``True`` would raise there and have the failure hidden by the
    error handler.
    """

    id = 999
    session = None

    def __init__(self) -> None:
        self.calls: list[object] = []
        #: file_ids Telegram should pretend it no longer recognises.
        self.reject_file_ids: set[str] = set()
        self._next_id = 100

    async def __call__(self, method, request_timeout=None):  # noqa: ANN001, ARG002
        self.calls.append(method)
        self._next_id += 1
        if isinstance(method, SendPhoto):
            if isinstance(method.photo, str) and method.photo in self.reject_file_ids:
                raise TelegramBadRequest(method=method, message="wrong file identifier")
            return _message(
                self._next_id,
                photo=[
                    PhotoSize(
                        file_id=f"file-{self._next_id}",
                        file_unique_id=f"uniq-{self._next_id}",
                        width=900,
                        height=1055,
                    )
                ],
            )
        if isinstance(method, SendMessage):
            return _message(self._next_id, text=method.text)
        return True

    @property
    def sent_texts(self) -> list[str]:
        return [c.text for c in self.calls if isinstance(c, SendMessage)]

    @property
    def sent_photos(self) -> list[SendPhoto]:
        return [c for c in self.calls if isinstance(c, SendPhoto)]

    @property
    def inline_answers(self) -> list[AnswerInlineQuery]:
        return [c for c in self.calls if isinstance(c, AnswerInlineQuery)]


def _message(message_id: int, **kwargs) -> Message:
    return Message(
        message_id=message_id,
        date=datetime.now(timezone.utc),
        chat=Chat(id=CHAT_ID, type="private"),
        from_user=User(id=USER_ID, is_bot=False, first_name="Tester"),
        **kwargs,
    )


def _update(text: str, message_id: int = 1) -> Update:
    return Update(update_id=message_id, message=_message(message_id, text=text))


def _inline_update(query: str, query_id: str = "q1", update_id: int = 10) -> Update:
    return Update(
        update_id=update_id,
        inline_query=InlineQuery(
            id=query_id,
            from_user=User(id=USER_ID, is_bot=False, first_name="Tester"),
            query=query,
            offset="",
        ),
    )


def _group_update(text: str, message_id: int) -> Update:
    return Update(
        update_id=message_id,
        message=Message(
            message_id=message_id,
            date=datetime.now(timezone.utc),
            chat=Chat(id=-100_123, type="supergroup"),
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
def _isolate(dispatcher, tmp_path, monkeypatch, caplog):
    """Fresh FSM and cache per test, and no stored provider unless a test asks."""
    dispatcher.fsm.storage = MemoryStorage()
    cache._entries.clear()
    monkeypatch.setattr("bot.services.db.DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr("bot.services.db._initialised", None)
    monkeypatch.setattr(
        "bot.middlewares.provider_ctx.get_user_provider", lambda _uid: None
    )
    yield
    # The catch-all error handler swallows exceptions by design, which would let a
    # broken handler pass as a green test. Only the error-handler test may log one.
    if "expect_error" not in caplog.text:
        assert not [r for r in caplog.records if r.levelname == "ERROR"], (
            "a handler raised and the error handler hid it"
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
        raise RuntimeError("expect_error: renderer exploded")

    monkeypatch.setattr("bot.handlers.phone.render_qr_card_async", boom)
    _feed(dispatcher, bot, "09123456789")

    assert not bot.sent_photos
    assert "went wrong" in bot.sent_texts[-1]


def test_help_lists_the_kbzpay_length_rule(dispatcher, bot):
    _feed(dispatcher, bot, "/help")
    assert "11-digit" in bot.sent_texts[0]


def test_an_unknown_command_says_so(dispatcher, bot):
    """Without a guard this fell through to "Numbers only, please"."""
    _feed(dispatcher, bot, "/halp")
    assert "don't know that command" in bot.sent_texts[0]


def test_a_group_message_is_ignored(dispatcher, bot, monkeypatch):
    """The phone handlers are catch-alls; in a group they must stay quiet."""
    _select(monkeypatch, Provider.WAVEPAY)
    asyncio.run(dispatcher.feed_update(bot, _group_update("09123456789", 7)))
    assert not bot.calls


def test_a_group_still_gets_start(dispatcher, bot):
    asyncio.run(dispatcher.feed_update(bot, _group_update("/start", 8)))
    assert bot.sent_texts


def test_decode_is_owner_only(dispatcher, bot, monkeypatch):
    monkeypatch.setattr("bot.config.OWNER_ID", 0)
    _feed(dispatcher, bot, "/decode")
    assert "don't know that command" in bot.sent_texts[0]


def test_the_owner_can_decode_a_pasted_qr(dispatcher, bot, monkeypatch):
    monkeypatch.setattr("bot.config.OWNER_ID", USER_ID)
    _feed(dispatcher, bot, f"/decode {kbzpay_qr_string('09123456789')}")

    report = bot.sent_texts[0]
    assert "42 bytes" in report
    assert "09123456789" in report


def test_a_repeat_number_is_answered_from_the_file_id_cache(
    dispatcher, bot, monkeypatch
):
    _select(monkeypatch, Provider.WAVEPAY)
    renders = 0
    original = renderer.render_qr_card

    def counting(*args, **kwargs):
        nonlocal renders
        renders += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(renderer, "render_qr_card", counting)

    _feed(dispatcher, bot, "09123456789")
    _feed(dispatcher, bot, "09123456789")

    assert renders == 1, "the second request should reuse the uploaded file_id"
    first, second = bot.sent_photos
    assert isinstance(first.photo, BufferedInputFile)
    assert second.photo == "file-101"
    assert len(cache) == 1


def test_a_rejected_file_id_falls_back_to_rendering(dispatcher, bot, monkeypatch):
    _select(monkeypatch, Provider.WAVEPAY)
    cache.put(Provider.WAVEPAY, "09123456789", "file-that-telegram-forgot")
    bot.reject_file_ids.add("file-that-telegram-forgot")

    _feed(dispatcher, bot, "09123456789")

    stale, fresh = bot.sent_photos
    assert stale.photo == "file-that-telegram-forgot"
    assert isinstance(fresh.photo, BufferedInputFile)
    assert cache.get(Provider.WAVEPAY, "09123456789") == "file-102"


def test_inline_without_cache_chat_id_offers_open_bot(dispatcher, bot, monkeypatch):
    monkeypatch.setattr("bot.config.QR_CACHE_CHAT_ID", 0)
    asyncio.run(dispatcher.feed_update(bot, _inline_update("09123456789")))
    assert bot.inline_answers
    answer = bot.inline_answers[0]
    assert answer.button.text == "Open the bot"
    assert answer.button.start_parameter == "start"


def test_inline_empty_query_prompts_for_number(dispatcher, bot, monkeypatch):
    monkeypatch.setattr("bot.config.QR_CACHE_CHAT_ID", -100123)
    asyncio.run(dispatcher.feed_update(bot, _inline_update("")))
    assert bot.inline_answers
    answer = bot.inline_answers[0]
    assert "Myanmar mobile number" in answer.button.text
    assert answer.button.start_parameter == "start"


def test_inline_bad_number_shows_bad_number_button(dispatcher, bot, monkeypatch):
    monkeypatch.setattr("bot.config.QR_CACHE_CHAT_ID", -100123)
    asyncio.run(dispatcher.feed_update(bot, _inline_update("invalid")))
    assert bot.inline_answers
    answer = bot.inline_answers[0]
    assert "Not a Myanmar mobile number" in answer.button.text
    assert answer.button.start_parameter == "start"

