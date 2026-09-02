from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot import texts
from bot.keyboards.provider_kb import provider_keyboard
from bot.services.providers import Provider

router = Router(name="start")


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


@router.message(F.text.startswith("/"))
async def unknown_command(message: Message, provider: Provider | None) -> None:
    """Anything command-shaped that got this far isn't one of ours.

    Without this it would fall through to the phone handler and come back as
    "Numbers only, please", which is a confusing answer to a typo like /halp.
    """
    await message.reply(
        texts.UNKNOWN_COMMAND, reply_markup=provider_keyboard(active=provider)
    )
