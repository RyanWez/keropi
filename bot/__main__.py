import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from aiogram.types import BotCommand

from bot import config
from bot.handlers import setup

logger = logging.getLogger(__name__)


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

    me = await bot.get_me()
    logger.info("Starting @%s (polling)", me.username)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
