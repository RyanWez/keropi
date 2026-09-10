"""The Mini App menu button published at startup, and its graceful failure.

Only the payload and the best-effort contract are tested here; the polling and
web-server wiring in ``main()`` is exercised by the dispatcher tests elsewhere.
"""

import asyncio
import logging

from aiogram.types import MenuButtonDefault, MenuButtonWebApp

from bot import config, texts
from bot.__main__ import publish_menu_button
from bot.services.languages import DEFAULT_LANGUAGE

APP_URL = "https://keropi-bot.onrender.com/"


class RecordingBot:
    """Stands in for the one Bot method publish_menu_button touches."""

    def __init__(self, error: Exception | None = None) -> None:
        self.calls: list[dict] = []
        self.error = error

    async def set_chat_menu_button(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return True


def _publish(monkeypatch, url: str | None) -> RecordingBot:
    monkeypatch.setattr(config, "WEB_APP_URL", url)
    bot = RecordingBot()
    asyncio.run(publish_menu_button(bot))
    return bot


def test_a_valid_url_publishes_a_web_app_menu_button(monkeypatch):
    (call,) = _publish(monkeypatch, APP_URL).calls
    button = call["menu_button"]
    assert isinstance(button, MenuButtonWebApp)
    assert button.web_app.url == APP_URL
    # No user context at startup, so the default language labels the button.
    assert button.text == texts.get(DEFAULT_LANGUAGE).WEB_APP_LABEL


def test_the_default_button_is_set_once_for_every_chat(monkeypatch):
    """Omitting chat_id changes the bot's *default* menu button, so one call at
    startup covers every private chat instead of one call per user."""
    (call,) = _publish(monkeypatch, APP_URL).calls
    assert "chat_id" not in call


def test_an_unset_url_clears_a_stale_button(monkeypatch):
    """A Mini App that was configured and then removed must not leave a button
    behind that points at a dead deploy; MenuButtonDefault restores the standard
    commands menu."""
    (call,) = _publish(monkeypatch, None).calls
    assert isinstance(call["menu_button"], MenuButtonDefault)


def test_a_refused_menu_button_does_not_halt_startup(monkeypatch, caplog):
    """publish_menu_button swallows API errors so polling always starts."""
    monkeypatch.setattr(config, "WEB_APP_URL", APP_URL)
    bot = RecordingBot(error=RuntimeError("431: something bad"))

    with caplog.at_level(logging.WARNING):
        asyncio.run(publish_menu_button(bot))  # must not raise

    assert len(bot.calls) == 1, "the call was attempted before failing"
    assert "menu button" in caplog.text
