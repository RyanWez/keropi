from aiogram import Router

from bot.handlers import phone, provider, start


def setup() -> Router:
    router = Router()
    router.include_routers(start.router, provider.router, phone.router)
    return router
