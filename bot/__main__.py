import asyncio
import logging

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from bot import config, texts
from bot.handlers import setup
from bot.middlewares.retry_after import RetryAfterMiddleware
from bot.middlewares.throttle import ThrottleMiddleware
from bot.services.languages import DEFAULT_LANGUAGE, Language

logger = logging.getLogger(__name__)


async def handle_health(request: web.Request) -> web.Response:
    return web.Response(text="OK - Keropi QR Bot is running", content_type="text/plain")


async def start_web_server(port: int) -> web.AppRunner:
    app = web.Application()
    app.router.add_get("/", handle_health)
    app.router.add_get("/health", handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("Health check server listening on port %s", port)
    return runner


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    # Outer, so a throttled update is dropped before any filter, database read or
    # render. Runs inside the dispatcher's own user-context middleware, which is
    # what puts event_from_user in the data dict.
    dp.update.outer_middleware(ThrottleMiddleware(cooldown=config.THROTTLE_SECONDS))
    dp.include_router(setup())
    return dp


async def publish_commands(bot: Bot) -> None:
    """Register the command menu, once per language.

    The entry without a language_code is the fallback for every client whose
    language has no dedicated list.
    """
    for language in Language:
        strings = texts.get(language)
        commands = [
            BotCommand(command="start", description=strings.COMMAND_START),
            BotCommand(command="help", description=strings.COMMAND_HELP),
            BotCommand(command="lang", description=strings.COMMAND_LANG),
        ]
        if language is DEFAULT_LANGUAGE:
            await bot.set_my_commands(commands)
        await bot.set_my_commands(commands, language_code=language.value)


async def main() -> None:
    config.setup_logging()
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    # Wraps every outgoing API call, so flood control is handled in one place.
    bot.session.middleware(RetryAfterMiddleware())

    dp = build_dispatcher()

    await publish_commands(bot)

    runner: web.AppRunner | None = None
    if config.PORT > 0:
        runner = await start_web_server(config.PORT)

    me = await bot.get_me()
    logger.info(
        "Starting @%s (polling, max %s concurrent updates, %s render workers)",
        me.username,
        config.MAX_CONCURRENT_UPDATES,
        config.RENDER_WORKERS,
    )
    try:
        await dp.start_polling(
            bot,
            # Bounds in-flight updates. aiogram acquires the semaphore in the polling
            # loop, so saturation slows getUpdates rather than piling up tasks.
            tasks_concurrency_limit=config.MAX_CONCURRENT_UPDATES,
        )
    finally:
        if runner:
            await runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
