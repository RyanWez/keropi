import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot import texts
from bot.keyboards.provider_kb import CALLBACK_PREFIX, provider_keyboard
from bot.services.db import get_user_provider, set_user_provider
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

    # Check if this provider is already currently active
    data = await state.get_data()
    current_provider = data.get("provider") or (
        get_user_provider(callback.from_user.id) if callback.from_user else None
    )

    if current_provider == provider.value:
        label = "KBZ Pay" if provider is Provider.KBZPAY else "WavePay"
        await callback.answer(f"✅ {label} is already selected!")
        return

    await state.set_state(QrFlow.waiting_phone)
    await state.update_data(provider=provider.value)
    if callback.from_user:
        set_user_provider(callback.from_user.id, provider.value)
        logger.info("user %s selected provider %s", callback.from_user.id, provider.value)

    if callback.message:
        await callback.message.answer(
            texts.ASK_PHONE[provider.value],
            reply_markup=provider_keyboard(active=provider),
        )
    await callback.answer()
