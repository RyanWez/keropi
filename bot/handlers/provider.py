import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot import texts
from bot.keyboards.provider_kb import CALLBACK_PREFIX, provider_keyboard
from bot.services.providers import Provider
from bot.states import QrFlow

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data.startswith(CALLBACK_PREFIX))
async def select_provider(callback: CallbackQuery, state: FSMContext) -> None:
    provider_value = callback.data.removeprefix(CALLBACK_PREFIX)
    try:
        provider = Provider(provider_value)
    except ValueError:
        await callback.answer("Unknown provider", show_alert=True)
        return

    await state.set_state(QrFlow.waiting_phone)
    await state.update_data(provider=provider.value)
    logger.info("chat %s selected provider %s", callback.message.chat.id, provider.value)

    await callback.message.answer(
        texts.ASK_PHONE[provider.value],
        reply_markup=provider_keyboard(active=provider),
    )
    await callback.answer()
