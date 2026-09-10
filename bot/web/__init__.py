"""The browser interface and JSON API for QR generation."""

import asyncio
import html
import json
import logging
import re
import time
from collections import defaultdict, deque
from pathlib import Path

from aiohttp import web

from bot.services.languages import DEFAULT_LANGUAGE, parse_language
from bot.services.providers import parse_provider
from bot.services.qr_generator import (
    AmountValidationError,
    PhoneValidationError,
    prepare_qr,
    render_prepared_qr,
)

logger = logging.getLogger(__name__)

_WEB_ROOT = Path(__file__).resolve().parent
_STATIC_ROOT = _WEB_ROOT / "static"
_IMAGES_ROOT = _WEB_ROOT.parent / "assets" / "images"
_INDEX_PATH = _WEB_ROOT / "index.html"
_MAX_BODY_BYTES = 1_024
_MAX_PHONE_CHARS = 40
_MAX_WEB_RENDERS = 6
_RENDER_SLOTS = asyncio.Semaphore(_MAX_WEB_RENDERS)
_RATE_LIMIT_WINDOW = 60.0
_RATE_LIMIT_REQUESTS = 20
_MAX_RATE_LIMIT_CLIENTS = 5_000
_REQUESTS_BY_CLIENT: dict[str, deque[float]] = defaultdict(deque)
_TAG_RE = re.compile(r"<[^>]*>")

_ERROR_MESSAGES = {
    "en": {
        "bad_request": "Please check the request and try again.",
        "bad_json": "The request must be valid JSON.",
        "bad_provider": "Choose KBZ Pay or WavePay.",
        "bad_phone_type": "Enter the phone number as text.",
        "phone_too_long": "That phone number is too long.",
        "bad_amount_type": "Enter the amount as text.",
        "amount_not_integer": "Enter a whole kyat amount, using digits and optional commas only.",
        "amount_leading_zero": "Remove leading zeros from the amount.",
        "amount_too_small": "The amount must be at least 1 MMK.",
        "amount_too_large": "The amount cannot exceed 999,999,999 MMK.",
        "amount_not_supported": "An amount can only be added to KBZ Pay QR codes.",
        "busy": "The generator is busy. Please try again in a moment.",
        "rate_limited": "Too many requests. Please wait a minute and try again.",
        "server_error": "We could not create the QR. Please try again.",
    },
    "my": {
        "bad_request": "ဖြည့်ထားသည့် အချက်အလက်များကို စစ်ပြီး ထပ်စမ်းပါ။",
        "bad_json": "တောင်းဆိုချက်သည် JSON ပုံစံမှန် ဖြစ်ရပါမည်။",
        "bad_provider": "KBZ Pay သို့မဟုတ် WavePay ကို ရွေးပါ။",
        "bad_phone_type": "ဖုန်းနံပါတ်ကို စာသားဖြင့် ထည့်ပါ။",
        "phone_too_long": "ဖုန်းနံပါတ် ရှည်လွန်းနေပါသည်။",
        "bad_amount_type": "ငွေပမာဏကို စာသားဖြင့် ထည့်ပါ။",
        "amount_not_integer": "ကျပ်ပြည့်ပမာဏကို ဂဏန်းနှင့် comma မှန်မှန်ဖြင့်သာ ထည့်ပါ။",
        "amount_leading_zero": "ငွေပမာဏရှေ့ရှိ သုညများကို ဖယ်ပါ။",
        "amount_too_small": "ငွေပမာဏသည် အနည်းဆုံး ၁ ကျပ် ဖြစ်ရပါမည်။",
        "amount_too_large": "ငွေပမာဏသည် ၉၉၉,၉၉၉,၉၉၉ ကျပ်ထက် မကျော်ရပါ။",
        "amount_not_supported": "ငွေပမာဏကို KBZ Pay QR အတွက်သာ ထည့်နိုင်ပါသည်။",
        "busy": "အသုံးပြုသူများနေပါသည်။ ခဏနေပြီး ထပ်စမ်းပါ။",
        "rate_limited": "တောင်းဆိုမှုများလွန်းနေပါသည်။ တစ်မိနစ်ခန့်စောင့်ပြီး ထပ်စမ်းပါ။",
        "server_error": "QR မပြုလုပ်နိုင်ပါ။ ထပ်စမ်းကြည့်ပါ။",
    },
}


@web.middleware
async def security_headers(request: web.Request, handler):
    response = await handler(request)
    if request.path.startswith(("/static/", "/images/")):
        response.headers["Cache-Control"] = "no-cache"
    response.headers.update(
        {
            "Content-Security-Policy": (
                "default-src 'self'; img-src 'self' blob:; "
                "style-src 'self'; script-src 'self'; "
                "connect-src 'self'; base-uri 'none'; form-action 'self'; "
                "frame-ancestors 'none'"
            ),
            "Cross-Origin-Opener-Policy": "same-origin",
            "Permissions-Policy": "camera=(), geolocation=(), microphone=()",
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
        }
    )
    return response


def _language(value: object) -> str:
    if isinstance(value, str):
        language = parse_language(value)
        if language is not None:
            return language.value
    return DEFAULT_LANGUAGE.value


def _error(message: str, *, status: int, code: str) -> web.Response:
    return web.json_response(
        {"ok": False, "error": {"code": code, "message": message}},
        status=status,
        headers={"Cache-Control": "no-store"},
    )


def _plain_text(message: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", message, flags=re.IGNORECASE)
    return html.unescape(_TAG_RE.sub("", text))


def _is_rate_limited(request: web.Request) -> bool:
    now = time.monotonic()
    client = request.remote or "unknown"
    attempts = _REQUESTS_BY_CLIENT[client]
    cutoff = now - _RATE_LIMIT_WINDOW
    while attempts and attempts[0] <= cutoff:
        attempts.popleft()
    if len(attempts) >= _RATE_LIMIT_REQUESTS:
        return True
    attempts.append(now)

    if len(_REQUESTS_BY_CLIENT) > _MAX_RATE_LIMIT_CLIENTS:
        stale_clients = [
            address
            for address, timestamps in _REQUESTS_BY_CLIENT.items()
            if not timestamps or timestamps[-1] <= cutoff
        ]
        for address in stale_clients:
            _REQUESTS_BY_CLIENT.pop(address, None)
    return False


async def handle_index(request: web.Request) -> web.FileResponse:
    return web.FileResponse(
        _INDEX_PATH,
        headers={"Cache-Control": "no-cache"},
    )


async def handle_health(request: web.Request) -> web.Response:
    return web.Response(
        text="OK - Keropi QR Bot is running",
        content_type="text/plain",
        headers={"Cache-Control": "no-store"},
    )


async def handle_qr(request: web.Request) -> web.Response:
    if _is_rate_limited(request):
        message = _ERROR_MESSAGES[DEFAULT_LANGUAGE.value]["rate_limited"]
        return _error(message, status=429, code="rate_limited")

    try:
        data = await request.json(loads=json.loads)
    except (json.JSONDecodeError, UnicodeDecodeError):
        message = _ERROR_MESSAGES[DEFAULT_LANGUAGE.value]["bad_json"]
        return _error(message, status=400, code="bad_json")

    if not isinstance(data, dict):
        message = _ERROR_MESSAGES[DEFAULT_LANGUAGE.value]["bad_request"]
        return _error(message, status=400, code="bad_request")

    language_code = _language(data.get("language"))
    messages = _ERROR_MESSAGES[language_code]
    provider_value = data.get("provider")
    provider = parse_provider(provider_value if isinstance(provider_value, str) else None)
    if provider is None:
        return _error(messages["bad_provider"], status=400, code="bad_provider")

    raw_phone = data.get("phone")
    if not isinstance(raw_phone, str):
        return _error(messages["bad_phone_type"], status=400, code="bad_phone_type")
    if len(raw_phone) > _MAX_PHONE_CHARS:
        return _error(messages["phone_too_long"], status=400, code="phone_too_long")

    raw_amount = data.get("amount")
    if raw_amount is not None and not isinstance(raw_amount, str):
        return _error(messages["bad_amount_type"], status=400, code="bad_amount_type")
    if isinstance(raw_amount, str) and len(raw_amount) > 20:
        return _error(messages["amount_too_large"], status=422, code="amount_too_large")

    language = parse_language(language_code) or DEFAULT_LANGUAGE
    try:
        prepared = prepare_qr(provider, raw_phone, language, raw_amount=raw_amount)
    except PhoneValidationError as exc:
        from bot import texts

        return _error(
            _plain_text(texts.get(language).phone_error(exc.check)),
            status=422,
            code=exc.check.reason.value if exc.check.reason else "invalid_phone",
        )
    except AmountValidationError as exc:
        code = exc.check.reason.value if exc.check.reason else "invalid_amount"
        return _error(messages.get(code, messages["bad_request"]), status=422, code=code)

    try:
        await asyncio.wait_for(_RENDER_SLOTS.acquire(), timeout=0.25)
    except TimeoutError:
        return _error(messages["busy"], status=503, code="busy")

    try:
        png = await render_prepared_qr(prepared)
    except Exception:
        logger.exception("web QR rendering failed for provider %s", provider.value)
        return _error(messages["server_error"], status=500, code="server_error")
    finally:
        _RENDER_SLOTS.release()

    logger.info("web QR generated (%s)", provider.value)
    headers = {
        "Cache-Control": "no-store",
        "Content-Disposition": f'inline; filename="{prepared.filename}"',
        "X-Normalized-Phone": prepared.phone,
        "X-Provider": provider.value,
    }
    if prepared.amount is not None:
        headers["X-Normalized-Amount"] = str(prepared.amount)
    return web.Response(
        body=png,
        content_type="image/png",
        headers=headers,
    )


def create_web_app(_args: list[str] | None = None) -> web.Application:
    app = web.Application(
        client_max_size=_MAX_BODY_BYTES,
        middlewares=[security_headers],
    )
    app.router.add_get("/", handle_index)
    app.router.add_get("/health", handle_health)
    app.router.add_post("/api/qr", handle_qr)
    app.router.add_static(
        "/static/",
        path=_STATIC_ROOT,
        name="static",
        append_version=True,
        follow_symlinks=False,
    )
    app.router.add_static(
        "/images/",
        path=_IMAGES_ROOT,
        name="images",
        append_version=False,
        follow_symlinks=False,
    )
    return app


async def start_web_server(port: int) -> web.AppRunner:
    app = create_web_app()
    runner = web.AppRunner(app, access_log=logger)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("Web app listening on port %s", port)
    return runner
