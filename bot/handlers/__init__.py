from aiogram import Router

from bot.handlers import diagnostics, errors, phone, provider, start
from bot.middlewares.provider_ctx import ProviderContextMiddleware

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
    provider_ctx = ProviderContextMiddleware()
    router.message.outer_middleware(provider_ctx)
    router.callback_query.outer_middleware(provider_ctx)
    router.include_routers(
        errors.router,
        diagnostics.router,
        start.router,
        provider.router,
        phone.router,
    )
    _root = router
    return router
