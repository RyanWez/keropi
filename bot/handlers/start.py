from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot import texts
from bot.keyboards.provider_kb import provider_keyboard
from bot.services.providers import Provider

router = Router()


@router.message(CommandStart())
async def cmd_start(
    message: Message, state: FSMContext, provider: Provider | None
) -> None:
    if provider is not None:
        await state.update_data(provider=provider.value)
    else:
        await state.clear()
    await message.reply(texts.WELCOME, reply_markup=provider_keyboard(active=provider))


@router.message(Command("help"))
async def cmd_help(message: Message, provider: Provider | None) -> None:
    await message.reply(texts.HELP, reply_markup=provider_keyboard(active=provider))
