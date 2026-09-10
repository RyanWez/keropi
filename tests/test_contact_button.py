"""Contact / feedback button on failures, the Mini App button on /start, and
validation of the URLs behind them."""

import pytest

from bot import config, texts
from bot.keyboards import (
    error_keyboard,
    language_keyboard,
    provider_keyboard,
    start_keyboard,
)
from bot.services.languages import Language
from bot.services.providers import Provider
from bot.services.validators import Reason, validate

EN = texts.get(Language.EN)
MY = texts.get(Language.MY)


def _rows(markup) -> list[list[str]]:
    return [[button.text for button in row] for row in markup.inline_keyboard]


def test_provider_keyboard_is_unchanged():
    assert _rows(provider_keyboard()) == [["KBZ Pay", "WavePay"]]
    assert _rows(provider_keyboard(Provider.WAVEPAY)) == [["KBZ Pay", "✅ WavePay"]]


def test_language_keyboard_uses_endonyms():
    """A user who picked the wrong language must still recognise the way back."""
    assert _rows(language_keyboard()) == [["English", "မြန်မာ"]]
    assert _rows(language_keyboard(Language.MY)) == [["English", "✅ မြန်မာ"]]
    assert _rows(language_keyboard(Language.EN)) == [["✅ English", "မြန်မာ"]]


def test_error_keyboard_is_contact_only_by_default():
    markup = error_keyboard(EN.CONTACT_LABEL, Provider.KBZPAY)
    assert _rows(markup) == [[EN.CONTACT_LABEL]]
    (button,) = markup.inline_keyboard[0]
    assert button.url == config.CONTACT_URL
    assert button.callback_data is None


def test_error_keyboard_keeps_the_providers_when_asked():
    markup = error_keyboard(EN.CONTACT_LABEL, Provider.KBZPAY, offer_providers=True)
    assert _rows(markup) == [["✅ KBZ Pay", "WavePay"], [EN.CONTACT_LABEL]]


def test_the_contact_label_is_translated():
    assert MY.CONTACT_LABEL != EN.CONTACT_LABEL
    assert _rows(error_keyboard(MY.CONTACT_LABEL)) == [[MY.CONTACT_LABEL]]


def test_error_keyboard_without_a_contact_url_degrades_to_providers(monkeypatch):
    """No button is better than a malformed URL: Telegram would reject the message."""
    monkeypatch.setattr(config, "CONTACT_URL", None)
    assert _rows(error_keyboard(EN.CONTACT_LABEL, Provider.WAVEPAY)) == [
        ["KBZ Pay", "✅ WavePay"]
    ]


def test_only_the_kbzpay_length_error_offers_a_provider_switch():
    """Its wording points at the WavePay button, so that row must stay."""
    short = validate("0912345678", Provider.KBZPAY)
    assert short.reason is Reason.KBZPAY_NEEDS_11
    assert texts.offers_provider_switch(short)

    for raw in ("0912345", "09abc456789", ""):
        check = validate(raw, Provider.WAVEPAY)
        assert not check.ok
        assert not texts.offers_provider_switch(check), raw


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("https://t.me/Super001z", "https://t.me/Super001z"),
        ("http://example.com/feedback", "http://example.com/feedback"),
        ("  https://t.me/Super001z  ", "https://t.me/Super001z"),
        # Not a usable button target.
        ("", None),
        ("not a url", None),
        ("ftp://example.com", None),
        ("javascript:alert(1)", None),
        ("tg://resolve?domain=x", None),
        ("https://", None),
        # A contact button pointing inside the host is a misconfiguration.
        ("http://localhost/x", None),
        ("http://127.0.0.1:8080", None),
        ("http://10.0.0.5/hook", None),
        ("http://192.168.1.1", None),
        ("http://169.254.169.254/latest/meta-data/", None),
    ],
)
def test_button_url_validation(monkeypatch, value, expected):
    monkeypatch.setenv("CONTACT_URL", value)
    assert config._button_url("CONTACT_URL") == expected


def test_an_unset_url_takes_the_default_but_an_empty_one_disables_it(monkeypatch):
    monkeypatch.delenv("CONTACT_URL", raising=False)
    assert config._button_url("CONTACT_URL", "https://t.me/Super001z") == (
        "https://t.me/Super001z"
    )

    monkeypatch.setenv("CONTACT_URL", "")
    assert config._button_url("CONTACT_URL", "https://t.me/Super001z") is None


APP_URL = "https://keropi-bot.onrender.com/"


def _web_app_buttons(markup) -> list:
    return [
        button
        for row in markup.inline_keyboard
        for button in row
        if button.web_app is not None
    ]


def test_start_keyboard_is_the_providers_alone_without_a_url():
    """conftest pins WEB_APP_URL empty, so the shipped default is no Mini App."""
    assert config.WEB_APP_URL is None
    markup = start_keyboard(EN.WEB_APP_LABEL, Provider.WAVEPAY, with_web_app=True)
    assert _rows(markup) == [["KBZ Pay", "✅ WavePay"]]
    assert not _web_app_buttons(markup)


def test_start_keyboard_adds_the_web_app_under_the_provider_row(monkeypatch):
    monkeypatch.setattr(config, "WEB_APP_URL", APP_URL)
    markup = start_keyboard(EN.WEB_APP_LABEL, Provider.KBZPAY, with_web_app=True)
    assert _rows(markup) == [["✅ KBZ Pay", "WavePay"], [EN.WEB_APP_LABEL]]
    (button,) = _web_app_buttons(markup)
    assert button.web_app.url == APP_URL
    # A web_app button carries neither a plain url nor a callback of its own.
    assert button.url is None
    assert button.callback_data is None


def test_start_keyboard_never_shows_a_web_app_button_in_a_group(monkeypatch):
    """Telegram only allows web_app buttons in private chats between a user and
    the bot, so the group /start stays on the provider row."""
    monkeypatch.setattr(config, "WEB_APP_URL", APP_URL)
    markup = start_keyboard(EN.WEB_APP_LABEL, Provider.KBZPAY, with_web_app=False)
    assert _rows(markup) == [["✅ KBZ Pay", "WavePay"]]
    assert not _web_app_buttons(markup)


def test_the_web_app_label_is_translated(monkeypatch):
    monkeypatch.setattr(config, "WEB_APP_URL", APP_URL)
    assert MY.WEB_APP_LABEL != EN.WEB_APP_LABEL
    markup = start_keyboard(MY.WEB_APP_LABEL, with_web_app=True)
    assert _rows(markup) == [["KBZ Pay", "WavePay"], [MY.WEB_APP_LABEL]]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("https://keropi-bot.onrender.com/", "https://keropi-bot.onrender.com/"),
        ("  https://example.com/app  ", "https://example.com/app"),
        # Plain http is a usable contact link, but Telegram won't launch a
        # Mini App from it, so for WEB_APP_URL it's a misconfiguration.
        ("http://example.com/", None),
        # Not usable at all.
        ("", None),
        ("not a url", None),
        ("ftp://example.com", None),
        ("javascript:alert(1)", None),
        ("https://", None),
        # A Mini App inside the host is unreachable for Telegram's clients.
        ("https://localhost/", None),
        ("https://keropi.localhost/", None),
        ("https://127.0.0.1:8443/", None),
        ("https://10.0.0.5/", None),
        ("https://192.168.1.1/", None),
        ("https://169.254.169.254/", None),
    ],
)
def test_web_app_url_must_be_public_https(monkeypatch, value, expected):
    monkeypatch.setenv("WEB_APP_URL", value)
    assert config._button_url("WEB_APP_URL", https_only=True) == expected


def test_web_app_stays_disabled_when_unset_or_empty(monkeypatch):
    """Unlike CONTACT_URL there is no sensible default host, so unset means off."""
    monkeypatch.delenv("WEB_APP_URL", raising=False)
    assert config._button_url("WEB_APP_URL", https_only=True) is None
    monkeypatch.setenv("WEB_APP_URL", "")
    assert config._button_url("WEB_APP_URL", https_only=True) is None
