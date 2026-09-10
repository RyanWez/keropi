import asyncio
import json
from io import BytesIO

import pytest
from aiohttp.test_utils import TestClient, TestServer
from PIL import Image

from bot.web import _REQUESTS_BY_CLIENT, create_web_app


def run_request(callback):
    async def execute():
        _REQUESTS_BY_CLIENT.clear()
        async with TestClient(TestServer(create_web_app())) as client:
            return await callback(client)

    return asyncio.run(execute())


def test_home_serves_the_web_app_with_security_headers():
    async def check(client):
        response = await client.get("/")
        body = await response.text()
        assert response.status == 200
        assert response.content_type == "text/html"
        assert "Keropi Pay QR" in body
        assert 'id="qr-form"' in body
        assert response.headers["X-Frame-Options"] == "DENY"
        assert "default-src 'self'" in response.headers["Content-Security-Policy"]

    run_request(check)


def test_static_assets_are_served():
    async def check(client):
        css = await client.get("/static/app.css")
        javascript = await client.get("/static/app.js")
        assert css.status == 200
        assert css.content_type == "text/css"
        assert "--green:" in await css.text()
        assert javascript.status == 200
        assert "generateQr" in await javascript.text()

    run_request(check)


@pytest.mark.parametrize("name", ["kbz.png", "wave.png"])
def test_provider_logos_are_served(name):
    async def check(client):
        response = await client.get(f"/images/{name}")
        body = await response.read()
        assert response.status == 200
        assert response.content_type == "image/png"
        image = Image.open(BytesIO(body))
        assert image.format == "PNG"
        assert image.width > 100 and image.height > 100

    run_request(check)


def test_health_stays_lightweight_and_uncached():
    async def check(client):
        response = await client.get("/health")
        assert response.status == 200
        assert await response.text() == "OK - Keropi QR Bot is running"
        assert response.headers["Cache-Control"] == "no-store"

    run_request(check)


@pytest.mark.parametrize(
    ("provider", "phone", "expected_phone"),
    [
        ("kbzpay", "+95 9 123 456 789", "09123456789"),
        ("wavepay", "09-1234-5678", "0912345678"),
    ],
)
def test_qr_api_returns_a_png(provider, phone, expected_phone):
    async def check(client):
        response = await client.post(
            "/api/qr",
            json={"provider": provider, "phone": phone, "language": "en"},
        )
        body = await response.read()
        assert response.status == 200
        assert response.content_type == "image/png"
        assert response.headers["Cache-Control"] == "no-store"
        assert response.headers["X-Normalized-Phone"] == expected_phone
        assert response.headers["X-Provider"] == provider
        assert f'{provider}_{expected_phone}.png' in response.headers["Content-Disposition"]
        image = Image.open(BytesIO(body))
        assert image.format == "PNG"
        assert image.width >= 900
        _scan_payload(body, provider, expected_phone)

    run_request(check)


def _scan_payload(png: bytes, provider: str, phone: str):
    """Decode the rendered card back and check it points at the right number."""
    zxingcpp = pytest.importorskip("zxingcpp", reason="zxing-cpp is a dev dependency")
    from bot.services.qr_decode import decode_qr_string

    (result,) = zxingcpp.read_barcodes(Image.open(BytesIO(png)))
    decoded = decode_qr_string(result.text)
    assert decoded.phone_digits == phone
    assert decoded.looks_like_kbzpay == (provider == "kbzpay")


def test_api_localises_validation_and_never_returns_telegram_markup():
    async def check(client):
        response = await client.post(
            "/api/qr",
            json={"provider": "kbzpay", "phone": "0912345678", "language": "my"},
        )
        payload = await response.json()
        assert response.status == 422
        assert payload["error"]["code"] == "kbzpay_needs_11"
        assert "၁၁" in payload["error"]["message"]
        assert "<b>" not in payload["error"]["message"]
        assert response.headers["Cache-Control"] == "no-store"

    run_request(check)


@pytest.mark.parametrize(
    ("body", "code"),
    [
        (b"not-json", "bad_json"),
        (json.dumps([]).encode(), "bad_request"),
        (json.dumps({"provider": "other", "phone": "09123456789"}).encode(), "bad_provider"),
        (json.dumps({"provider": "wavepay", "phone": 9123456789}).encode(), "bad_phone_type"),
    ],
)
def test_api_rejects_malformed_requests(body, code):
    async def check(client):
        response = await client.post(
            "/api/qr", data=body, headers={"Content-Type": "application/json"}
        )
        payload = await response.json()
        assert response.status == 400
        assert payload["ok"] is False
        assert payload["error"]["code"] == code

    run_request(check)


def test_api_limits_request_body_size():
    async def check(client):
        response = await client.post(
            "/api/qr",
            data=b'{' + b'"padding":"' + b"x" * 2_000 + b'"}',
            headers={"Content-Type": "application/json"},
        )
        assert response.status == 413

    run_request(check)


def _csp_directives(header: str) -> dict[str, set[str]]:
    directives = {}
    for part in header.split(";"):
        tokens = part.split()
        if tokens:
            directives[tokens[0]] = set(tokens[1:])
    return directives


def test_index_loads_the_official_telegram_sdk_before_app_js():
    async def check(client):
        response = await client.get("/")
        body = await response.text()
        assert response.status == 200
        assert 'src="https://telegram.org/js/telegram-web-app.js"' in body
        assert body.index("telegram.org/js/telegram-web-app.js") < body.index(
            'src="/static/app.js"'
        )
        # viewport-fit=cover lets the layout see the OS safe-area insets.
        assert "viewport-fit=cover" in body

    run_request(check)


def test_csp_grants_only_self_plus_telegram_org_and_keeps_restrictions():
    async def check(client):
        for path in ("/", "/static/app.js", "/static/app.css"):
            response = await client.get(path)
            csp = response.headers["Content-Security-Policy"]
            directives = _csp_directives(csp)
            assert directives["script-src"] == {"'self'", "https://telegram.org"}
            assert directives["default-src"] == {"'self'"}
            assert directives["img-src"] == {"'self'", "blob:"}
            assert directives["connect-src"] == {"'self'"}
            assert directives["frame-ancestors"] == {"'none'"}
            assert directives["base-uri"] == {"'none'"}
            assert directives["form-action"] == {"'self'"}
            allowed = {"'self'", "'none'", "blob:", "https://telegram.org"}
            for name, sources in directives.items():
                assert sources <= allowed, f"{name} references an outside source"
            assert "unsafe-inline" not in csp
            assert "unsafe-eval" not in csp
            assert response.headers["X-Frame-Options"] == "DENY"
            assert response.headers["X-Content-Type-Options"] == "nosniff"

    run_request(check)


def test_app_js_is_telegram_mini_app_ready_with_browser_fallback():
    async def check(client):
        response = await client.get("/static/app.js")
        javascript = await response.text()
        # Feature detection: a plain browser must keep working untouched.
        assert "window.Telegram?.WebApp" in javascript
        assert "if (!telegramApp) return;" in javascript
        assert "telegramApp.ready()" in javascript
        assert "telegramApp.expand()" in javascript
        # ready()/expand() run after the UI has been initialised.
        assert javascript.rstrip().endswith("initTelegramApp();")
        # Theme, viewport height and safe areas react to Telegram data/events.
        assert "themeParams" in javascript
        assert "themeChanged" in javascript
        assert "viewportChanged" in javascript
        assert "safeAreaChanged" in javascript
        assert "contentSafeAreaChanged" in javascript
        assert "--telegram-viewport-height" in javascript
        assert "--telegram-safe-inset-" in javascript
        # initDataUnsafe is only used as a language presentation hint.
        assert "initDataUnsafe?.user?.language_code" in javascript
        # The API request body must not carry any Telegram data.
        assert "JSON.stringify({ provider, phone: phoneInput.value, amount, language })" in javascript

    run_request(check)


def test_app_css_adapts_safe_area_and_viewport_with_fallbacks():
    async def check(client):
        response = await client.get("/static/app.css")
        css = await response.text()
        assert css.count("--safe-area-top: 0px;") == 1
        assert css.count("env(safe-area-inset-top)") >= 1
        assert "max(env(safe-area-inset-top), var(--telegram-safe-inset-top, 0px))" in css
        assert "max(env(safe-area-inset-bottom), var(--telegram-safe-inset-bottom, 0px))" in css
        assert "var(--telegram-viewport-height, 100dvh)" in css

    run_request(check)
