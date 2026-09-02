"""Per-user cooldown.

Telegram allows a bot roughly 30 messages per second overall and one per second per
chat. Exceeding it earns a 429 that stalls the bot for *every* user, so this is a
capacity guard rather than an access control: anyone may use the bot, but nobody
gets to monopolise it.

Registered as an outer middleware on the update observer, ahead of filters, so a
throttled update costs no rendering and no database read.
"""

import logging
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from bot import texts
from bot.services.languages import from_telegram, parse_language

logger = logging.getLogger(__name__)


@dataclass
class _Seen:
    last_handled: float
    last_warned: float = 0.0


class ThrottleMiddleware(BaseMiddleware):
    """Drops updates from a user who is inside their cooldown window.

    The user is told once per window; further updates in the same window are
    dropped silently so a held-down send key cannot turn into a reply storm.
    """

    def __init__(self, cooldown: float = 2.0, capacity: int = 10_000) -> None:
        self.cooldown = cooldown
        self.capacity = capacity
        self._seen: OrderedDict[int, _Seen] = OrderedDict()

    def _remember(self, user_id: int, entry: _Seen) -> None:
        self._seen[user_id] = entry
        self._seen.move_to_end(user_id)
        while len(self._seen) > self.capacity:
            self._seen.popitem(last=False)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        now = time.monotonic()
        entry = self._seen.get(user.id)
        if entry is None or now - entry.last_handled >= self.cooldown:
            self._remember(user.id, _Seen(last_handled=now))
            return await handler(event, data)

        if now - entry.last_warned >= self.cooldown:
            entry.last_warned = now
            await self._notify(event, user)
        self._seen.move_to_end(user.id)
        logger.debug("throttled user %s", user.id)
        return None

    @staticmethod
    async def _notify(event: TelegramObject, user: Any) -> None:
        if not isinstance(event, Update):
            return

        # This middleware runs before the settings middleware, so the saved language
        # is looked up here. It fires at most once per cooldown window per user.
        from bot.services.db import get_user_lang

        lang = parse_language(get_user_lang(user.id)) or from_telegram(
            getattr(user, "language_code", None)
        )
        notice = texts.get(lang).COOLDOWN_NOTICE

        try:
            if event.callback_query is not None:
                # Answer it regardless, or the client keeps spinning.
                await event.callback_query.answer(notice)
            elif event.message is not None:
                await event.message.reply(notice)
        except Exception:
            # Telling the user is a courtesy. Nothing here may turn a throttled
            # update into an error, so this catch is deliberately broad.
            logger.debug("could not deliver cooldown notice", exc_info=True)
