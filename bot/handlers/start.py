from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot import texts
from bot.keyboards import error_keyboard, language_keyboard, provider_keyboard
from bot.services.languages import Language
from bot.services.providers import Provider

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(
    message: Message, state: FSMContext, provider: Provider | None, lang: Language
) -> None:
    await state.update_data(lang=lang.value)
    if provider is not None:
        await state.update_data(provider=provider.value)
    await message.reply(
        texts.get(lang).WELCOME, reply_markup=provider_keyboard(active=provider)
    )


@router.message(Command("help"))
async def cmd_help(message: Message, provider: Provider | None, lang: Language) -> None:
    await message.reply(
        texts.get(lang).HELP, reply_markup=provider_keyboard(active=provider)
    )


@router.message(Command("lang"))
async def cmd_lang(message: Message, lang: Language) -> None:
    await message.reply(
        texts.get(lang).LANG_PROMPT, reply_markup=language_keyboard(active=lang)
    )


@router.message(F.text.startswith("/"))
async def unknown_command(
    message: Message, provider: Provider | None, lang: Language
) -> None:
    """Anything command-shaped that got this far isn't one of ours.

    Without this it would fall through to the phone handler and come back as
    "Numbers only, please", which is a confusing answer to a typo like /halp.
    """
    strings = texts.get(lang)
    await message.reply(
        strings.UNKNOWN_COMMAND,
        reply_markup=error_keyboard(strings.CONTACT_LABEL, provider),
    )
