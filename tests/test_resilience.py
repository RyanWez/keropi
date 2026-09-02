"""Throttle, flood-control retry and the file_id cache."""

import asyncio
from datetime import datetime, timezone

import pytest
from aiogram.exceptions import TelegramRetryAfter, TelegramServerError
from aiogram.methods import SendMessage
from aiogram.types import Chat, Message, TelegramObject, Update, User

from bot.middlewares.retry_after import RetryAfterMiddleware
from bot.middlewares.throttle import ThrottleMiddleware
from bot.services.providers import Provider
from bot.services.qr_cache import FileIdCache

KBZ = Provider.KBZPAY
WAVE = Provider.WAVEPAY


def _update(user_id: int) -> Update:
    return Update(
        update_id=user_id,
        message=Message(
            message_id=1,
            date=datetime.now(timezone.utc),
            chat=Chat(id=user_id, type="private"),
            from_user=User(id=user_id, is_bot=False, first_name="T"),
            text="09123456789",
        ),
    )


class _Counter:
    def __init__(self) -> None:
        self.calls = 0

    async def __call__(self, event, data):  # noqa: ANN001, ARG002
        self.calls += 1
        return "handled"


def _data(user_id: int) -> dict:
    return {"event_from_user": User(id=user_id, is_bot=False, first_name="T")}


def test_throttle_lets_the_first_update_through():
    mw, handler = ThrottleMiddleware(cooldown=60), _Counter()
    result = asyncio.run(mw(handler, _update(1), _data(1)))
    assert result == "handled"
    assert handler.calls == 1


def test_throttle_drops_a_burst_from_one_user():
    mw, handler = ThrottleMiddleware(cooldown=60), _Counter()

    async def burst():
        return [await mw(handler, _update(1), _data(1)) for _ in range(5)]

    results = asyncio.run(burst())
    assert handler.calls == 1
    assert results[1:] == [None] * 4


def test_throttle_warns_once_then_stays_quiet():
    """A held-down send key must not turn into a reply storm."""
    mw, handler = ThrottleMiddleware(cooldown=60), _Counter()
    notices: list[TelegramObject] = []

    async def record(event):
        notices.append(event)

    mw._notify = record

    async def burst():
        for _ in range(5):
            await mw(handler, _update(1), _data(1))

    asyncio.run(burst())
    assert len(notices) == 1


def test_throttle_is_per_user():
    mw, handler = ThrottleMiddleware(cooldown=60), _Counter()

    async def two_users():
        await mw(handler, _update(1), _data(1))
        await mw(handler, _update(2), _data(2))

    asyncio.run(two_users())
    assert handler.calls == 2, "one busy user must not block anybody else"


def test_throttle_releases_after_the_cooldown():
    mw, handler = ThrottleMiddleware(cooldown=0.05), _Counter()

    async def wait_it_out():
        await mw(handler, _update(1), _data(1))
        await asyncio.sleep(0.06)
        await mw(handler, _update(1), _data(1))

    asyncio.run(wait_it_out())
    assert handler.calls == 2


def test_throttle_memory_is_bounded():
    mw, handler = ThrottleMiddleware(cooldown=60, capacity=10), _Counter()

    async def many_users():
        for user_id in range(50):
            await mw(handler, _update(user_id), _data(user_id))

    asyncio.run(many_users())
    assert len(mw._seen) == 10


def test_throttle_ignores_events_without_a_user():
    mw, handler = ThrottleMiddleware(cooldown=60), _Counter()
    asyncio.run(mw(handler, _update(1), {}))
    asyncio.run(mw(handler, _update(1), {}))
    assert handler.calls == 2


class _FlakyTransport:
    """Raises the given exceptions in order, then succeeds."""

    def __init__(self, *errors: Exception) -> None:
        self.errors = list(errors)
        self.attempts = 0

    async def __call__(self, bot, method):  # noqa: ANN001, ARG002
        self.attempts += 1
        if self.errors:
            raise self.errors.pop(0)
        return "ok"


def _method() -> SendMessage:
    return SendMessage(chat_id=1, text="hi")


def test_retry_waits_out_flood_control(monkeypatch):
    slept: list[float] = []
    monkeypatch.setattr(asyncio, "sleep", lambda d: slept.append(d) or _noop())
    transport = _FlakyTransport(
        TelegramRetryAfter(method=_method(), message="slow down", retry_after=3)
    )
    mw = RetryAfterMiddleware(attempts=3)

    assert asyncio.run(mw(transport, None, _method())) == "ok"
    assert transport.attempts == 2
    assert slept == [3]


def test_retry_gives_up_after_the_last_attempt(monkeypatch):
    monkeypatch.setattr(asyncio, "sleep", lambda _d: _noop())
    transport = _FlakyTransport(
        *[
            TelegramRetryAfter(method=_method(), message="slow down", retry_after=1)
            for _ in range(3)
        ]
    )
    mw = RetryAfterMiddleware(attempts=3)

    with pytest.raises(TelegramRetryAfter):
        asyncio.run(mw(transport, None, _method()))
    assert transport.attempts == 3


def test_retry_refuses_to_sit_out_an_absurd_wait(monkeypatch):
    monkeypatch.setattr(asyncio, "sleep", lambda _d: _noop())
    transport = _FlakyTransport(
        TelegramRetryAfter(method=_method(), message="slow down", retry_after=600)
    )
    mw = RetryAfterMiddleware(attempts=3, max_wait=30)

    with pytest.raises(TelegramRetryAfter):
        asyncio.run(mw(transport, None, _method()))
    assert transport.attempts == 1, "the user is still waiting; fail fast instead"


def test_retry_also_covers_telegram_server_errors(monkeypatch):
    monkeypatch.setattr(asyncio, "sleep", lambda _d: _noop())
    transport = _FlakyTransport(
        TelegramServerError(method=_method(), message="bad gateway")
    )
    assert asyncio.run(RetryAfterMiddleware()(transport, None, _method())) == "ok"


async def _noop() -> None:
    return None


def test_cache_round_trip():
    cache = FileIdCache(capacity=10)
    assert cache.get(KBZ, "09123456789") is None

    cache.put(KBZ, "09123456789", "file-a")
    assert cache.get(KBZ, "09123456789") == "file-a"
    assert cache.get(WAVE, "09123456789") is None, "providers must not share entries"


def test_cache_treats_a_warning_as_a_different_card():
    cache = FileIdCache(capacity=10)
    cache.put(KBZ, "09123456789", "plain")
    cache.put(KBZ, "09123456789", "warned", warning="careful")

    assert cache.get(KBZ, "09123456789") == "plain"
    assert cache.get(KBZ, "09123456789", warning="careful") == "warned"


def test_cache_evicts_the_least_recently_used():
    cache = FileIdCache(capacity=2)
    cache.put(WAVE, "091111111", "a")
    cache.put(WAVE, "092222222", "b")
    cache.get(WAVE, "091111111")  # touch it, so "b" becomes the oldest
    cache.put(WAVE, "093333333", "c")

    assert len(cache) == 2
    assert cache.get(WAVE, "091111111") == "a"
    assert cache.get(WAVE, "092222222") is None
    assert cache.get(WAVE, "093333333") == "c"


def test_cache_discard():
    cache = FileIdCache(capacity=2)
    cache.put(WAVE, "091111111", "a")
    cache.discard(WAVE, "091111111")
    assert cache.get(WAVE, "091111111") is None


def test_a_zero_capacity_cache_stores_nothing():
    cache = FileIdCache(capacity=0)
    cache.put(WAVE, "091111111", "a")
    assert len(cache) == 0
