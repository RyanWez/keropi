"""User-facing copy, in every language the bot speaks.

One ``Strings`` record per language, so adding a language means adding one record
and nothing else. Handlers do ``t = texts.get(lang)`` and read fields off it, which
keeps the wording out of the logic and makes a missing translation a startup-time
type error rather than a runtime surprise.

Provider names (KBZ Pay, WavePay) are brands and stay as they are everywhere.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from bot.services.languages import DEFAULT_LANGUAGE, Language
from bot.services.providers import Provider
from bot.services.validators import PhoneCheck, Reason


@dataclass(frozen=True, slots=True)
class Strings:
    WELCOME: str
    ASK_PHONE: Mapping[Provider, str]
    NO_PROVIDER: str
    NOT_TEXT: str
    UNKNOWN_COMMAND: str
    QR_CAPTION: str
    #: Drawn onto the card image, so it must stay short and avoid glyphs the
    #: bundled fonts lack. tests/test_card_text.py enforces that.
    PADDING_WARNING: str
    HELP: str
    PHONE_ERRORS: Mapping[Reason, str]
    ERROR_REPLY: str
    ERROR_ALERT: str
    COOLDOWN_NOTICE: str
    CONTACT_LABEL: str
    PROVIDER_ALREADY: str
    LANG_PROMPT: str
    LANG_CHANGED: str
    LANG_ALREADY: str
    INLINE_PROMPT: str
    INLINE_BAD_NUMBER: str
    INLINE_OPEN_BOT: str
    COMMAND_START: str
    COMMAND_HELP: str
    COMMAND_LANG: str

    def phone_error(self, check: PhoneCheck) -> str:
        template = self.PHONE_ERRORS.get(check.reason) or self.PHONE_ERRORS[Reason.EMPTY]
        return template.format(digits=check.digits)


#: The only rejection whose text points at a provider button, so that row has to
#: stay on screen. For every other failure, switching provider is not the fix.
_REASONS_WITH_PROVIDER_REMEDY = frozenset({Reason.KBZPAY_NEEDS_11})


def offers_provider_switch(check: PhoneCheck) -> bool:
    return check.reason in _REASONS_WITH_PROVIDER_REMEDY


EN = Strings(
    WELCOME=(
        "👋 <b>Pay QR Generator</b>\n\n"
        "Send me a customer's phone number and I will turn it into a "
        "payment QR code you can scan — so you never have to type the "
        "number into the transfer screen again.\n\n"
        "✅ <b>KBZ Pay</b> — KBZPay-ready QR\n"
        "✅ <b>WavePay</b> — WavePay-ready QR\n\n"
        "Pick a provider below to get started. 👇"
    ),
    ASK_PHONE={
        Provider.KBZPAY: (
            "📱 <b>KBZ Pay</b> selected.\n\n"
            "Now send the customer's phone number "
            "(e.g. <code>09xxxxxxxxx</code>) and I'll return the QR."
        ),
        Provider.WAVEPAY: (
            "📱 <b>WavePay</b> selected.\n\n"
            "Now send the customer's phone number "
            "(e.g. <code>09xxxxxxxxx</code>) and I'll return the QR."
        ),
    },
    NO_PROVIDER="Please choose a provider first. 👇",
    NOT_TEXT="Please send the phone number as text (e.g. <code>09xxxxxxxxx</code>).",
    UNKNOWN_COMMAND=(
        "I don't know that command. Use /start to pick a provider, "
        "/help for instructions, or /lang to change language."
    ),
    QR_CAPTION=(
        "📷 Scan with <b>{label}</b>\n"
        "Number: <code>{phone}</code>\n\n"
        "⚠️ Verify recipient name before sending.\n"
        "<i>Note: This bot does not check if the account exists. "
        "Please verify recipient details yourself.</i>"
    ),
    PADDING_WARNING="UNVERIFIED short-number format - check the name!",
    HELP=(
        "📖 <b>How to use Pay QR Generator</b>\n\n"
        "1️⃣ Choose your payment provider: <b>KBZ Pay</b> or <b>WavePay</b>.\n"
        "2️⃣ Send the recipient's Myanmar mobile number (e.g. <code>09xxxxxxxxx</code>).\n"
        "3️⃣ The bot will instantly return a branded, high-resolution QR card.\n"
        "4️⃣ Open your KBZPay or WavePay app and scan the QR code to transfer "
        "directly without typing the number.\n\n"
        "<b>Number formats</b>\n"
        "• <code>09xxxxxxxxx</code>, <code>+959xxxxxxxxx</code> and "
        "<code>959xxxxxxxxx</code> all work — spaces, dashes and brackets are "
        "cleaned up for you.\n"
        "• <b>KBZ Pay</b> needs an 11-digit number. Its QR stores the number in a "
        "fixed-width field that only 11 digits fill exactly.\n"
        "• <b>WavePay</b> also accepts the older 9- and 10-digit numbers.\n\n"
        "💡 You can switch providers anytime using the inline buttons below.\n"
        "🌐 Use /lang to change language.\n"
        "⏱ There is a short cooldown between requests so the bot stays "
        "responsive for everyone."
    ),
    PHONE_ERRORS={
        Reason.EMPTY: (
            "Please send a Myanmar mobile number, e.g. <code>09xxxxxxxxx</code>."
        ),
        Reason.NOT_DIGITS: (
            "⚠️ Numbers only, please. Letters and symbols aren't allowed.\n"
            "Example: <code>09xxxxxxxxx</code>"
        ),
        Reason.NOT_MYANMAR_MOBILE: (
            "⚠️ That doesn't look like a Myanmar mobile number ({digits} digits).\n\n"
            "Mobile numbers start with <code>09</code> and are 9, 10 or 11 digits "
            "long — for example <code>09xxxxxxxxx</code>. <code>+959…</code> and "
            "<code>959…</code> are fine too.\n"
            "Numbers starting <code>01</code> are landlines and can't receive a "
            "wallet transfer."
        ),
        Reason.KBZPAY_NEEDS_11: (
            "⚠️ <b>KBZ Pay needs an 11-digit number.</b> You sent {digits} digits.\n\n"
            "KBZPay's QR stores the number in a fixed-width field that only 11 "
            "digits fill exactly, so I can't build a reliable QR for a shorter one "
            "— a wrong QR could point at someone else's account.\n\n"
            "Myanmar still has older 9- and 10-digit numbers, so this may well be "
            "genuine. Two options:\n"
            "• Ask the recipient for their 11-digit number, or\n"
            "• Switch to <b>WavePay</b> below — it accepts this length."
        ),
    },
    ERROR_REPLY=(
        "😕 Something went wrong on my side and I couldn't build that QR.\n"
        "Please try again — if it keeps happening, send /start to reset."
    ),
    ERROR_ALERT="Something went wrong. Please try again.",
    COOLDOWN_NOTICE="⏳ One moment — please wait a couple of seconds between numbers.",
    CONTACT_LABEL="💬 Contact & Feedback",
    PROVIDER_ALREADY="✅ {label} is already selected!",
    LANG_PROMPT="🌐 <b>Language</b>\n\nWhich language should I reply in? 👇",
    LANG_CHANGED=(
        "✅ Language set to <b>{name}</b>.\n\n"
        "Send a phone number to get a QR, or /help for instructions."
    ),
    LANG_ALREADY="✅ {name} is already selected!",
    INLINE_PROMPT="Type a Myanmar mobile number, e.g. 09xxxxxxxxx",
    INLINE_BAD_NUMBER="Not a Myanmar mobile number — tap to open the bot",
    INLINE_OPEN_BOT="Open the bot",
    COMMAND_START="Start bot & choose provider",
    COMMAND_HELP="How to use this bot",
    COMMAND_LANG="Change language",
)
MY = Strings(
    WELCOME=(
        "👋 <b>ငွေလွှဲ QR ပြုလုပ်ပေးသည့် Bot</b>\n\n"
        "ဖုန်းနံပါတ် ပို့လိုက်ရုံဖြင့် Scan ဖတ် ငွေလွှဲနိုင်သော QR ကုဒ် ချက်ချင်း ထုတ်ပေးပါမည်။\n\n"
        "စတင်ရန် အောက်တွင် ရွေးချယ်ပါ 👇"
    ),
    ASK_PHONE={
        Provider.KBZPAY: (
            "📱 <b>KBZ Pay</b> ကို ရွေးချယ်ထားပါသည်။\n\n"
            "လက်ခံသူ၏ ဖုန်းနံပါတ် ပို့ပေးပါ (ဥပမာ <code>09xxxxxxxxx</code>)။"
        ),
        Provider.WAVEPAY: (
            "📱 <b>WavePay</b> ကို ရွေးချယ်ထားပါသည်။\n\n"
            "လက်ခံသူ၏ ဖုန်းနံပါတ် ပို့ပေးပါ (ဥပမာ <code>09xxxxxxxxx</code>)။"
        ),
    },
    NO_PROVIDER="အသုံးပြုလိုသည့် Pay ကို အောက်တွင် အရင်ရွေးပေးပါ 👇",
    NOT_TEXT="ဖုန်းနံပါတ်ကို စာဖြင့် ရိုက်ပို့ပေးပါ (ဥပမာ <code>09xxxxxxxxx</code>)။",
    UNKNOWN_COMMAND=(
        "ဒီ command မရှိပါ။ စတင်ရန် /start ၊ "
        "အသုံးပြုနည်းအတွက် /help ၊ ဘာသာစကားအတွက် /lang ကို သုံးပါ။"
    ),
    QR_CAPTION=(
        "📷 <b>{label}</b> ဖြင့် Scan ဖတ်ပါ\n"
        "နံပါတ် — <code>{phone}</code>\n\n"
        "⚠️ ငွေမလွှဲမီ လက်ခံသူအမည်ကို သေချာစစ်ဆေးပါ\n"
        "<i>(အကောင့် အမှန်တကယ် ရှိ/မရှိ ကိုယ်တိုင် အတည်ပြုပေးပါ)</i>"
    ),
    PADDING_WARNING="အတည်မပြုရသေးသော ပုံစံ၊ နာမည် စစ်ပါ",
    HELP=(
        "📖 <b>အသုံးပြုနည်း</b>\n\n"
        "1️⃣ ငွေလွှဲမည့် Pay ရွေးပါ (<b>KBZ Pay</b> သို့မဟုတ် <b>WavePay</b>)။\n"
        "2️⃣ လက်ခံသူ ဖုန်းနံပါတ် ပို့ပါ (ဥပမာ <code>09xxxxxxxxx</code>)။\n"
        "3️⃣ ရရှိလာသော QR ကို သက်ဆိုင်ရာ App ဖြင့် Scan ဖတ်၍ ငွေလွှဲပါ။\n\n"
        "<b>နံပါတ် ပုံစံများ -</b>\n"
        "• <code>09…</code>၊ <code>+959…</code>၊ <code>959…</code> အားလုံး ပို့နိုင်ပါသည် (space, dash များ အလိုအလျောက် ဖယ်ပေးသည်)။\n"
        "• <b>KBZ Pay:</b> ဂဏန်း ၁၁ လုံး နံပါတ်သာ ရပါမည်။\n"
        "• <b>WavePay:</b> ဂဏန်း ၉၊ ၁၀၊ ၁၁ လုံး နံပါတ်အားလုံး ရပါသည်။\n\n"
        "🌐 ဘာသာစကား ပြောင်းရန် — /lang"
    ),
    PHONE_ERRORS={
        Reason.EMPTY: (
            "မြန်မာ ဖုန်းနံပါတ် ပို့ပေးပါ (ဥပမာ <code>09xxxxxxxxx</code>)။"
        ),
        Reason.NOT_DIGITS: (
            "⚠️ ဂဏန်း (နံပါတ်) သာ ထည့်ပါ။ အက္ခရာနှင့် သင်္ကေတများ လက်မခံပါ။\n"
            "ဥပမာ — <code>09xxxxxxxxx</code>"
        ),
        Reason.NOT_MYANMAR_MOBILE: (
            "⚠️ မြန်မာ မိုဘိုင်းဖုန်းနံပါတ် မဟုတ်ပါ (ဂဏန်း {digits} လုံး ဖြစ်နေပါသည်)။\n\n"
            "မိုဘိုင်းနံပါတ်သည် <code>09</code> ဖြင့် စတင်ရမည်ဖြစ်ပြီး ဂဏန်း ၉ လုံး၊ ၁၀ လုံး သို့မဟုတ် ၁၁ လုံး ရှိရပါမည် (ဥပမာ <code>09xxxxxxxxx</code>)။\n"
            "<i>(ကြိုးဖုန်းနံပါတ်များဖြင့် ငွေလွှဲ၍ မရပါ)</i>"
        ),
        Reason.KBZPAY_NEEDS_11: (
            "⚠️ <b>KBZ Pay အတွက် ဂဏန်း ၁၁ လုံး လိုအပ်ပါသည်</b> "
            "(ပို့လိုက်သော နံပါတ်မှာ {digits} လုံး ဖြစ်နေပါသည်)။\n\n"
            "KBZ Pay QR စနစ်သည် ၁၁ လုံး နံပါတ်သာ အတိအကျ လက်ခံပါသည်။\n\n"
            "• လက်ခံသူထံမှ ၁၁ လုံး နံပါတ် အသစ်တောင်းပါ သို့မဟုတ်\n"
            "• အောက်တွင် <b>WavePay</b> သို့ ပြောင်းသုံးပါ (၉ လုံး၊ ၁၀ လုံး လက်ခံပါသည်)။"
        ),
    },
    ERROR_REPLY=(
        "😕 QR ထုတ်ပေးရာတွင် အခက်အခဲ တစ်ခု ရှိနေပါသည်။\n"
        "ထပ်မံ စမ်းသပ်ပေးပါ။ ဆက်ဖြစ်နေပါက /start ဖြင့် ပြန်လည် စတင်ပါ။"
    ),
    ERROR_ALERT="တစ်ခုခု မှားယွင်းနေပါသည်။ ထပ်စမ်းကြည့်ပေးပါ။",
    COOLDOWN_NOTICE="⏳ ခဏစောင့်ပါ — နံပါတ်တစ်ခုနှင့် တစ်ခုကြား ၂ စက္ကန့်ခန့် ခြားပေးပါ။",
    CONTACT_LABEL="💬 ဆက်သွယ်ရန် / အကြံပြုရန်",
    PROVIDER_ALREADY="✅ {label} ကို ရွေးထားပြီးသားပါ။",
    LANG_PROMPT="🌐 <b>ဘာသာစကား ရွေးချယ်ရန်</b>\n\nအသုံးပြုလိုသည့် ဘာသာစကားကို ရွေးပါ 👇",
    LANG_CHANGED=(
        "✅ ဘာသာစကားကို <b>{name}</b> သို့ ပြောင်းလိုက်ပါပြီ။\n\n"
        "ဖုန်းနံပါတ် ပို့ပေးပါက QR ထုတ်ပေးပါမည် (အသုံးပြုနည်းအတွက် /help)။"
    ),
    LANG_ALREADY="✅ {name} ကို ရွေးထားပြီးသားပါ။",
    INLINE_PROMPT="မြန်မာ ဖုန်းနံပါတ် ရိုက်ထည့်ပါ (ဥပမာ 09xxxxxxxxx)",
    INLINE_BAD_NUMBER="မြန်မာ မိုဘိုင်းနံပါတ် မဟုတ်ပါ — Bot ဖွင့်ရန် နှိပ်ပါ",
    INLINE_OPEN_BOT="Bot ကို ဖွင့်ပါ",
    COMMAND_START="စတင်ရန် / Provider ရွေးရန်",
    COMMAND_HELP="အသုံးပြုနည်း",
    COMMAND_LANG="ဘာသာစကား ပြောင်းရန်",
)
# <<<STRINGS>>>

STRINGS: Mapping[Language, Strings] = {Language.EN: EN, Language.MY: MY}


def get(lang: Language | None = None) -> Strings:
    """Strings for ``lang``, falling back to the default rather than raising."""
    return STRINGS.get(lang or DEFAULT_LANGUAGE, STRINGS[DEFAULT_LANGUAGE])
