import asyncio
import logging
import os

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from bot import config
from bot.handlers import setup

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


async def main() -> None:
    config.setup_logging()
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(setup())

    await bot.set_my_commands([
        BotCommand(command="start", description="Start bot & choose provider"),
        BotCommand(command="help", description="How to use this bot"),
    ])

    port = int(os.getenv("PORT", "0"))
    runner: web.AppRunner | None = None
    if port > 0:
        runner = await start_web_server(port)

    me = await bot.get_me()
    logger.info("Starting @%s (polling)", me.username)
    try:
        await dp.start_polling(bot)
    finally:
        if runner:
            await runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
