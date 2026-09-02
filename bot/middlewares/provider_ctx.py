"""Resolves the user's selected provider once per update.

Every handler used to repeat "look in FSM state, fall back to the database", which
meant five copies of the same lookup and five chances for them to drift apart.

Registered as an outer middleware on the message and callback observers, so the
dispatcher's own user-context and FSM middlewares have already populated ``data``.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from bot.services.db import get_user_provider
from bot.services.providers import Provider, parse_provider


class ProviderContextMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        data["provider"] = await self.resolve(data)
        return await handler(event, data)

    @staticmethod
    async def resolve(data: dict[str, Any]) -> Provider | None:
        state = data.get("state")
        if state is not None:
            stored = (await state.get_data()).get("provider")
            provider = parse_provider(stored)
            if provider is not None:
                return provider

        user = data.get("event_from_user")
        if user is None:
            return None
        return parse_provider(get_user_provider(user.id))
