"""Catch-all error handler.

Without one, an unexpected exception is swallowed by the dispatcher and the user
gets nothing back at all — the request just appears to vanish.
"""

import logging

from aiogram import Router
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from aiogram.types import ErrorEvent

from bot import texts
from bot.keyboards import error_keyboard
from bot.services.db import get_user_lang
from bot.services.languages import from_telegram, parse_language

logger = logging.getLogger(__name__)
router = Router(name="errors")


def _strings(event: ErrorEvent) -> texts.Strings:
    """Resolve the user's language directly.

    aiogram's error middleware is the outermost one, so it wraps the user-context
    middleware and ErrorEvent carries only the raw update. The user has to be dug
    out of it by hand.
    """
    update = event.update
    for carrier in (update.message, update.callback_query, update.inline_query):
        if carrier is not None and carrier.from_user is not None:
            user = carrier.from_user
            break
    else:
        return texts.get()

    lang = parse_language(get_user_lang(user.id)) or from_telegram(user.language_code)
    return texts.get(lang)


async def _notify(event: ErrorEvent) -> None:
    """Best-effort apology. Never let this raise: we are already handling an error."""
    strings = _strings(event)
    update = event.update

    callback = update.callback_query
    if callback is not None:
        try:
            await callback.answer(strings.ERROR_ALERT, show_alert=True)
        except TelegramAPIError:
            logger.debug("could not answer callback after error", exc_info=True)
        return

    message = update.message
    if message is None:
        return
    try:
        await message.reply(
            strings.ERROR_REPLY,
            reply_markup=error_keyboard(strings.CONTACT_LABEL),
        )
    except TelegramAPIError:
        logger.debug("could not reply after error", exc_info=True)


@router.error()
async def on_error(event: ErrorEvent) -> bool:
    exception = event.exception

    if isinstance(exception, TelegramForbiddenError):
        # The user blocked the bot or left the chat. Nothing to say and nowhere to say it.
        logger.info("forbidden: %s", exception)
        return True

    if isinstance(exception, TelegramRetryAfter):
        # The session middleware already retried and gave up.
        logger.warning("flood limit hit, %s seconds requested", exception.retry_after)
        await _notify(event)
        return True

    logger.exception(
        "unhandled error on update %s: %s",
        event.update.update_id,
        exception,
        exc_info=exception,
    )
    await _notify(event)
    return True
