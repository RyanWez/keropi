from aiogram import Router

from bot.handlers import diagnostics, errors, inline, language, phone, provider, start
from bot.middlewares.settings import SettingsMiddleware

_root: Router | None = None


def setup() -> Router:
    """Build the handler tree.

    Memoised because aiogram routers are module-level singletons and a Router may
    only ever have one parent, so composing them twice would raise.

    Order matters: diagnostics claims the owner's photos before phone's catch-all,
    and start claims commands before phone treats them as phone numbers.
    """
    global _root
    if _root is not None:
        return _root

    router = Router(name="root")
    settings = SettingsMiddleware()
    router.message.outer_middleware(settings)
    router.callback_query.outer_middleware(settings)
    router.inline_query.outer_middleware(settings)
    router.include_routers(
        errors.router,
        diagnostics.router,
        start.router,
        provider.router,
        language.router,
        inline.router,
        phone.router,
    )
    _root = router
    return router
