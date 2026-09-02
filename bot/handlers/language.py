"""Language selection, mirroring how the provider buttons behave."""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot import texts
from bot.keyboards import LANG_PREFIX, language_keyboard
from bot.services.db import set_user_lang
from bot.services.languages import LANGUAGE_NAMES, Language, parse_language

logger = logging.getLogger(__name__)
router = Router(name="language")


@router.callback_query(F.data.startswith(LANG_PREFIX))
async def select_language(
    callback: CallbackQuery, state: FSMContext, lang: Language
) -> None:
    chosen = parse_language(callback.data.removeprefix(LANG_PREFIX))
    if chosen is None:
        await callback.answer("Unknown language", show_alert=True)
        return

    name = LANGUAGE_NAMES[chosen]
    if chosen is lang:
        # Already active: a toast is enough, and re-sending the message would just
        # repeat what is already on screen.
        await callback.answer(texts.get(lang).LANG_ALREADY.format(name=name))
        return

    await state.update_data(lang=chosen.value)
    if callback.from_user:
        set_user_lang(callback.from_user.id, chosen.value)
        logger.info("user %s selected language %s", callback.from_user.id, chosen.value)

    if callback.message:
        # Confirmation is written in the new language, so it doubles as a preview.
        await callback.message.answer(
            texts.get(chosen).LANG_CHANGED.format(name=name),
            reply_markup=language_keyboard(active=chosen),
        )
    await callback.answer()
