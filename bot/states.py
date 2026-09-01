from aiogram.fsm.state import State, StatesGroup


class QrFlow(StatesGroup):
    waiting_phone = State()
