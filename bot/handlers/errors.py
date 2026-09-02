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
from bot.keyboards.provider_kb import error_keyboard

logger = logging.getLogger(__name__)
router = Router(name="errors")


async def _notify(event: ErrorEvent) -> None:
    """Best-effort apology. Never let this raise: we are already handling an error."""
    update = event.update
    callback = update.callback_query
    if callback is not None:
        try:
            await callback.answer(texts.ERROR_ALERT, show_alert=True)
        except TelegramAPIError:
            logger.debug("could not answer callback after error", exc_info=True)
        return

    message = update.message
    if message is None:
        return
    try:
        await message.reply(texts.ERROR_REPLY, reply_markup=error_keyboard())
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
