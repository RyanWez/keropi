"""The /lang flow, and that every reply honours the chosen language."""

import asyncio
from datetime import datetime, timezone

import pytest
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.methods import AnswerCallbackQuery, SendMessage, SendPhoto
from aiogram.types import CallbackQuery, Chat, Message, PhotoSize, Update, User

from bot import texts
from bot.services import db
from bot.services.languages import Language
from bot.services.providers import Provider
from bot.services.validators import Reason

CHAT_ID = 6_000_001
USER_ID = 6_000_002

EN = texts.get(Language.EN)
MY = texts.get(Language.MY)


class RecordingBot:
    id = 999
    session = None

    def __init__(self) -> None:
        self.calls: list[object] = []
        self._next_id = 200

    async def __call__(self, method, request_timeout=None):  # noqa: ANN001, ARG002
        self.calls.append(method)
        self._next_id += 1
        if isinstance(method, SendPhoto):
            return _message(
                self._next_id,
                photo=[
                    PhotoSize(
                        file_id=f"file-{self._next_id}",
                        file_unique_id=f"uniq-{self._next_id}",
                        width=900,
                        height=1103,
                    )
                ],
            )
        if isinstance(method, SendMessage):
            return _message(self._next_id, text=method.text)
        return True

    @property
    def texts(self) -> list[str]:
        return [c.text for c in self.calls if isinstance(c, SendMessage)]

    @property
    def toasts(self) -> list[str | None]:
        return [c.text for c in self.calls if isinstance(c, AnswerCallbackQuery)]

    @property
    def photos(self) -> list[SendPhoto]:
        return [c for c in self.calls if isinstance(c, SendPhoto)]

    @property
    def keyboards(self) -> list[list[list[str]]]:
        return [
            [[b.text for b in row] for row in c.reply_markup.inline_keyboard]
            for c in self.calls
            if getattr(c, "reply_markup", None) is not None
        ]


def _message(message_id: int, *, language_code: str | None = None, **kwargs) -> Message:
    return Message(
        message_id=message_id,
        date=datetime.now(timezone.utc),
        chat=Chat(id=CHAT_ID, type="private"),
        from_user=User(
            id=USER_ID, is_bot=False, first_name="Tester", language_code=language_code
        ),
        **kwargs,
    )


def _text_update(text: str, *, language_code: str | None = None) -> Update:
    return Update(
        update_id=1, message=_message(1, language_code=language_code, text=text)
    )


def _tap(data: str) -> Update:
    return Update(
        update_id=2,
        callback_query=CallbackQuery(
            id="cb1",
            from_user=User(id=USER_ID, is_bot=False, first_name="Tester"),
            chat_instance="ci",
            data=data,
            message=_message(3, text="anything"),
        ),
    )


@pytest.fixture(autouse=True)
def _fresh_fsm(dispatcher):
    dispatcher.fsm.storage = MemoryStorage()


@pytest.fixture
def bot() -> RecordingBot:
    return RecordingBot()


def _feed(dp: Dispatcher, bot: RecordingBot, update: Update) -> None:
    asyncio.run(dp.feed_update(bot, update))


def test_lang_shows_both_languages(dispatcher, bot):
    _feed(dispatcher, bot, _text_update("/lang"))

    assert bot.texts == [EN.LANG_PROMPT]
    assert bot.keyboards == [[["✅ English", "မြန်မာ"]]]


def test_choosing_myanmar_confirms_in_myanmar_and_ticks_it(dispatcher, bot):
    _feed(dispatcher, bot, _tap("lang:my"))

    assert bot.texts == [MY.LANG_CHANGED.format(name="မြန်မာ")]
    assert bot.keyboards == [[["English", "✅ မြန်မာ"]]]
    # The toast is empty: the confirmation message already said it.
    assert bot.toasts == [None]
    assert db.get_user_lang(USER_ID) == "my"


def test_choosing_the_active_language_only_shows_a_toast(dispatcher, bot):
    db.set_user_lang(USER_ID, "my")
    _feed(dispatcher, bot, _tap("lang:my"))

    assert bot.texts == [], "no new message for a choice that changes nothing"
    assert bot.toasts == [MY.LANG_ALREADY.format(name="မြန်မာ")]


def test_english_is_the_active_default(dispatcher, bot):
    _feed(dispatcher, bot, _tap("lang:en"))
    assert bot.texts == []
    assert bot.toasts == [EN.LANG_ALREADY.format(name="English")]


def test_an_unknown_language_is_refused(dispatcher, bot):
    _feed(dispatcher, bot, _tap("lang:klingon"))
    assert bot.texts == []
    assert bot.toasts == ["Unknown language"]
    assert db.get_user_lang(USER_ID) is None


def test_the_provider_toast_is_translated(dispatcher, bot):
    db.set_user_lang(USER_ID, "my")
    db.set_user_provider(USER_ID, Provider.KBZPAY.value)
    _feed(dispatcher, bot, _tap("provider:kbzpay"))

    assert bot.toasts == [MY.PROVIDER_ALREADY.format(label="KBZ Pay")]


def test_choosing_a_provider_asks_for_the_number_in_myanmar(dispatcher, bot):
    db.set_user_lang(USER_ID, "my")
    _feed(dispatcher, bot, _tap("provider:wavepay"))

    assert bot.texts == [MY.ASK_PHONE[Provider.WAVEPAY]]


@pytest.mark.parametrize(
    ("command", "field"),
    [("/start", "WELCOME"), ("/help", "HELP"), ("/halp", "UNKNOWN_COMMAND")],
)
def test_commands_reply_in_the_chosen_language(dispatcher, bot, command, field):
    db.set_user_lang(USER_ID, "my")
    _feed(dispatcher, bot, _text_update(command))

    assert bot.texts == [getattr(MY, field)]


def test_a_rejected_number_explains_itself_in_myanmar(dispatcher, bot):
    db.set_user_lang(USER_ID, "my")
    db.set_user_provider(USER_ID, Provider.KBZPAY.value)
    _feed(dispatcher, bot, _text_update("0912345678"))

    assert not bot.photos
    (reply,) = bot.texts
    assert reply == MY.PHONE_ERRORS[Reason.KBZPAY_NEEDS_11].format(digits=10)
    assert bot.keyboards == [[["✅ KBZ Pay", "WavePay"], [MY.CONTACT_LABEL]]]


def test_the_qr_caption_is_translated(dispatcher, bot):
    db.set_user_lang(USER_ID, "my")
    db.set_user_provider(USER_ID, Provider.WAVEPAY.value)
    _feed(dispatcher, bot, _text_update("09123456789"))

    (photo,) = bot.photos
    assert photo.caption == MY.QR_CAPTION.format(label="WavePay", phone="09123456789")


def test_a_first_time_myanmar_client_gets_myanmar(dispatcher, bot):
    """Telegram tells us the client's language; it beats guessing English."""
    _feed(dispatcher, bot, _text_update("/start", language_code="my"))
    assert bot.texts == [MY.WELCOME]


def test_a_first_time_english_client_gets_english(dispatcher, bot):
    _feed(dispatcher, bot, _text_update("/start", language_code="en-GB"))
    assert bot.texts == [EN.WELCOME]


def test_a_saved_choice_beats_the_client_language(dispatcher, bot):
    db.set_user_lang(USER_ID, "en")
    _feed(dispatcher, bot, _text_update("/start", language_code="my"))
    assert bot.texts == [EN.WELCOME]


def test_setting_a_language_leaves_the_provider_alone(dispatcher, bot):
    db.set_user_provider(USER_ID, Provider.KBZPAY.value)
    _feed(dispatcher, bot, _tap("lang:my"))

    assert db.get_user_settings(USER_ID) == (Provider.KBZPAY.value, "my")
