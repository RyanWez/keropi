import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot import texts
from bot.keyboards.provider_kb import CALLBACK_PREFIX, LABELS, provider_keyboard
from bot.services.db import set_user_provider
from bot.services.providers import Provider, parse_provider

logger = logging.getLogger(__name__)
router = Router(name="provider")


@router.callback_query(F.data.startswith(CALLBACK_PREFIX))
async def select_provider(
    callback: CallbackQuery, state: FSMContext, provider: Provider | None
) -> None:
    chosen = parse_provider(callback.data.removeprefix(CALLBACK_PREFIX))
    if chosen is None:
        await callback.answer("Unknown provider", show_alert=True)
        return

    if chosen is provider:
        await callback.answer(f"✅ {LABELS[chosen]} is already selected!")
        return

    await state.update_data(provider=chosen.value)
    if callback.from_user:
        set_user_provider(callback.from_user.id, chosen.value)
        logger.info("user %s selected provider %s", callback.from_user.id, chosen.value)

    if callback.message:
        await callback.message.answer(
            texts.ASK_PHONE[chosen.value],
            reply_markup=provider_keyboard(active=chosen),
        )
    await callback.answer()
