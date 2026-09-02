"""Resolves the user's saved provider and language once per update.

Every handler used to repeat "look in FSM state, fall back to the database", which
meant several copies of the same lookup and several chances for them to drift apart.
Both preferences come from one row, so one query serves both.

Registered as an outer middleware on the message and callback observers, so the
dispatcher's own user-context and FSM middlewares have already populated ``data``.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

from bot.services.db import get_user_settings
from bot.services.languages import Language, from_telegram, parse_language
from bot.services.providers import Provider, parse_provider


class SettingsMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        provider, lang = await self.resolve(data)
        data["provider"] = provider
        data["lang"] = lang
        return await handler(event, data)

    @staticmethod
    async def resolve(data: dict[str, Any]) -> tuple[Provider | None, Language]:
        state = data.get("state")
        cached = await state.get_data() if state is not None else {}

        provider = parse_provider(cached.get("provider"))
        lang = parse_language(cached.get("lang"))
        if provider is not None and lang is not None:
            return provider, lang

        user: User | None = data.get("event_from_user")
        if user is None:
            # No user means no preferences to look up; the Telegram client language
            # is unavailable too, so fall back to the default.
            return provider, lang or from_telegram(None)

        stored_provider, stored_lang = get_user_settings(user.id)
        provider = provider or parse_provider(stored_provider)
        # A user who has never chosen gets their Telegram client's language, which
        # is a better first guess than English for a Myanmar audience.
        lang = lang or parse_language(stored_lang) or from_telegram(user.language_code)
        return provider, lang
