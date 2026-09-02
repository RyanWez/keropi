"""Honours Telegram's flood-control back-off.

aiogram has no built-in retry: check_response raises TelegramRetryAfter as soon as
the response carries parameters.retry_after. This wraps every outgoing API call, so
one caller does not have to remember to handle it.
"""

import asyncio
import logging

from aiogram import Bot
from aiogram.client.session.middlewares.base import (
    BaseRequestMiddleware,
    NextRequestMiddlewareType,
)
from aiogram.exceptions import TelegramRetryAfter, TelegramServerError
from aiogram.methods import Response, TelegramMethod
from aiogram.methods.base import TelegramType

logger = logging.getLogger(__name__)


class RetryAfterMiddleware(BaseRequestMiddleware):
    def __init__(self, attempts: int = 3, max_wait: float = 30.0) -> None:
        self.attempts = attempts
        #: Waiting longer than this is worse than failing: the user is still there.
        self.max_wait = max_wait

    async def __call__(
        self,
        make_request: NextRequestMiddlewareType[TelegramType],
        bot: Bot,
        method: TelegramMethod[TelegramType],
    ) -> Response[TelegramType]:
        for attempt in range(1, self.attempts + 1):
            try:
                return await make_request(bot, method)
            except TelegramRetryAfter as error:
                if attempt == self.attempts or error.retry_after > self.max_wait:
                    raise
                logger.warning(
                    "%s hit flood control, waiting %ss (attempt %s/%s)",
                    type(method).__name__,
                    error.retry_after,
                    attempt,
                    self.attempts,
                )
                await asyncio.sleep(error.retry_after)
            except TelegramServerError as error:
                if attempt == self.attempts:
                    raise
                delay = 2.0**attempt
                logger.warning(
                    "%s got a server error (%s), retrying in %ss",
                    type(method).__name__,
                    error,
                    delay,
                )
                await asyncio.sleep(delay)
        raise RuntimeError("unreachable: loop either returns or raises")
