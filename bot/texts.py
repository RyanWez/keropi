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
        "👋 <b>ငွေလွှဲ QR ထုတ်ပေးစက်</b>\n\n"
        "ဖုန်းနံပါတ် ပို့လိုက်ရင် scan ဖတ်လို့ရတဲ့ ငွေလွှဲ QR ကုဒ် ပြန်ပေးပါမယ်။ "
        "ငွေလွှဲစာမျက်နှာမှာ နံပါတ် လိုက်ရိုက်နေရတာ မလိုတော့ပါဘူး။\n\n"
        "✅ <b>KBZ Pay</b> — KBZPay နဲ့ ဖတ်လို့ရတဲ့ QR\n"
        "✅ <b>WavePay</b> — WavePay နဲ့ ဖတ်လို့ရတဲ့ QR\n\n"
        "စတင်ဖို့ အောက်မှာ ရွေးပါ။ 👇"
    ),
    ASK_PHONE={
        Provider.KBZPAY: (
            "📱 <b>KBZ Pay</b> ကို ရွေးထားပါတယ်။\n\n"
            "လက်ခံသူရဲ့ ဖုန်းနံပါတ် (ဥပမာ <code>09xxxxxxxxx</code>) ပို့လိုက်ပါ။ "
            "QR ပြန်ပေးပါမယ်။"
        ),
        Provider.WAVEPAY: (
            "📱 <b>WavePay</b> ကို ရွေးထားပါတယ်။\n\n"
            "လက်ခံသူရဲ့ ဖုန်းနံပါတ် (ဥပမာ <code>09xxxxxxxxx</code>) ပို့လိုက်ပါ။ "
            "QR ပြန်ပေးပါမယ်။"
        ),
    },
    NO_PROVIDER="ဘယ် app နဲ့ လွှဲမလဲ အောက်မှာ အရင် ရွေးပါ။ 👇",
    NOT_TEXT="ဖုန်းနံပါတ်ကို စာသားအနေနဲ့ ပို့ပေးပါ (ဥပမာ <code>09xxxxxxxxx</code>)။",
    UNKNOWN_COMMAND=(
        "ဒီ command ကို မသိပါဘူး။ /start နဲ့ app ရွေးပါ၊ "
        "အသုံးပြုနည်းအတွက် /help ၊ ဘာသာစကား ပြောင်းရန် /lang ။"
    ),
    QR_CAPTION=(
        "📷 <b>{label}</b> နဲ့ scan ဖတ်ပါ\n"
        "နံပါတ် — <code>{phone}</code>\n\n"
        "⚠️ ငွေမလွှဲခင် လက်ခံသူ နာမည်ကို အတည်ပြုပါ။\n"
        "<i>ဒီ bot က အကောင့် တကယ်ရှိမရှိ စစ်မပေးပါဘူး။ "
        "လက်ခံသူ အချက်အလက်ကို ကိုယ်တိုင် စစ်ပေးပါ။</i>"
    ),
    PADDING_WARNING="အတည်မပြုရသေးသော ပုံစံ၊ နာမည် စစ်ပါ",
    HELP=(
        "📖 <b>အသုံးပြုနည်း</b>\n\n"
        "1️⃣ ငွေပေးချေမှု app ရွေးပါ — <b>KBZ Pay</b> ဒါမှမဟုတ် <b>WavePay</b>။\n"
        "2️⃣ လက်ခံသူရဲ့ မြန်မာ ဖုန်းနံပါတ် ပို့ပါ (ဥပမာ <code>09xxxxxxxxx</code>)။\n"
        "3️⃣ QR ကုဒ် ကဒ်ပြားကို ချက်ချင်း ပြန်ပေးပါမယ်။\n"
        "4️⃣ KBZPay ဒါမှမဟုတ် WavePay app ကို ဖွင့်ပြီး QR ကို scan ဖတ်လိုက်ရင် "
        "နံပါတ် ရိုက်ထည့်စရာ မလိုဘဲ ငွေလွှဲနိုင်ပါတယ်။\n\n"
        "<b>နံပါတ် ပုံစံများ</b>\n"
        "• <code>09xxxxxxxxx</code>၊ <code>+959xxxxxxxxx</code>၊ "
        "<code>959xxxxxxxxx</code> အားလုံး ရပါတယ် — space၊ dash၊ ကွင်းစကွင်းပိတ်တွေကို "
        "အလိုအလျောက် ဖယ်ပေးပါတယ်။\n"
        "• <b>KBZ Pay</b> အတွက် ဂဏန်း ၁၁ လုံး လိုအပ်ပါတယ်။ သူ့ QR က နံပါတ်ကို အရှည် "
        "အတိအကျ သတ်မှတ်ထားတဲ့ အကွက်ထဲ ထည့်ရတာဖြစ်လို့ ၁၁ လုံးပဲ အံကိုက် ဝင်ပါတယ်။\n"
        "• <b>WavePay</b> ကတော့ ဂဏန်း ၉ လုံး၊ ၁၀ လုံး နံပါတ်အဟောင်းတွေကိုပါ "
        "လက်ခံပါတယ်။\n\n"
        "💡 အောက်က button တွေနဲ့ အချိန်မရွေး ပြောင်းလို့ ရပါတယ်။\n"
        "🌐 ဘာသာစကား ပြောင်းရန် /lang ။\n"
        "⏱ Bot က အားလုံးအတွက် အလုပ်လုပ်နိုင်ဖို့ တစ်ခါပို့ပြီးရင် စောင့်ရတဲ့ အချိန် "
        "အနည်းငယ် ရှိပါတယ်။"
    ),
    PHONE_ERRORS={
        Reason.EMPTY: (
            "မြန်မာ ဖုန်းနံပါတ် တစ်လုံး ပို့ပေးပါ (ဥပမာ <code>09xxxxxxxxx</code>)။"
        ),
        Reason.NOT_DIGITS: (
            "⚠️ ဂဏန်းသာ ထည့်ပါ။ အက္ခရာနဲ့ သင်္ကေတတွေ လက်ခံမပါဘူး။\n"
            "ဥပမာ — <code>09xxxxxxxxx</code>"
        ),
        Reason.NOT_MYANMAR_MOBILE: (
            "⚠️ ဒါက မြန်မာ မိုဘိုင်း နံပါတ် မဟုတ်ပုံရပါတယ် (ဂဏန်း {digits} လုံး)။\n\n"
            "မိုဘိုင်း နံပါတ်က <code>09</code> နဲ့ စပြီး ဂဏန်း ၉ လုံး၊ ၁၀ လုံး "
            "ဒါမှမဟုတ် ၁၁ လုံး ရှိပါတယ် — ဥပမာ <code>09xxxxxxxxx</code>။ "
            "<code>+959…</code> နဲ့ <code>959…</code> လည်း ရပါတယ်။\n"
            "<code>01</code> နဲ့ စတဲ့ နံပါတ်တွေက ကြိုးဖုန်းတွေဖြစ်လို့ "
            "ငွေလက်ခံလို့ မရပါဘူး။"
        ),
        Reason.KBZPAY_NEEDS_11: (
            "⚠️ <b>KBZ Pay အတွက် ဂဏန်း ၁၁ လုံး လိုအပ်ပါတယ်။</b> "
            "ခင်ဗျား ပို့တာ ဂဏန်း {digits} လုံးပါ။\n\n"
            "KBZPay ရဲ့ QR က နံပါတ်ကို အရှည် အတိအကျ သတ်မှတ်ထားတဲ့ အကွက်ထဲ "
            "ထည့်ရတာဖြစ်ပြီး ၁၁ လုံးပဲ အံကိုက် ဝင်ပါတယ်။ ဒါကြောင့် ဒီအရှည်အတွက် "
            "စိတ်ချရတဲ့ QR ထုတ်လို့ မရပါဘူး — QR မှားရင် တခြားသူရဲ့ အကောင့်ကို "
            "ရောက်သွားနိုင်ပါတယ်။\n\n"
            "မြန်မာမှာ ဂဏန်း ၉ လုံး၊ ၁၀ လုံး နံပါတ်အဟောင်းတွေ ရှိနေဆဲဖြစ်လို့ "
            "ဒီနံပါတ်က တကယ် ဖြစ်နိုင်ပါတယ်။ လမ်း ၂ လမ်း ရှိပါတယ် —\n"
            "• လက်ခံသူဆီက ဂဏန်း ၁၁ လုံး နံပါတ် ပြန်တောင်းပါ၊ ဒါမှမဟုတ်\n"
            "• အောက်မှာ <b>WavePay</b> ကို ပြောင်းပါ — ဒီအရှည်ကို လက်ခံပါတယ်။"
        ),
    },
    ERROR_REPLY=(
        "😕 ကျွန်တော့်ဘက်မှာ ပြဿနာ တစ်ခု တက်လို့ QR ထုတ်လို့ မရလိုက်ပါဘူး။\n"
        "ထပ်စမ်းကြည့်ပေးပါ။ ဆက်ဖြစ်နေရင် /start နဲ့ အစကနေ ပြန်စပါ။"
    ),
    ERROR_ALERT="ပြဿနာ တစ်ခု တက်သွားပါတယ်။ ထပ်စမ်းကြည့်ပါ။",
    COOLDOWN_NOTICE="⏳ ခဏလေး စောင့်ပါ — နံပါတ် တစ်လုံးနဲ့ တစ်လုံး ကြားမှာ နှစ်စက္ကန့်လောက် ခြားပေးပါ။",
    CONTACT_LABEL="💬 ဆက်သွယ်ရန် / အကြံပြုရန်",
    PROVIDER_ALREADY="✅ {label} ကို ရွေးထားပြီးသားပါ။",
    LANG_PROMPT="🌐 <b>ဘာသာစကား</b>\n\nဘယ်ဘာသာနဲ့ ပြန်ဖြေရမလဲ ရွေးပါ။ 👇",
    LANG_CHANGED=(
        "✅ ဘာသာစကားကို <b>{name}</b> ပြောင်းလိုက်ပါပြီ။\n\n"
        "ဖုန်းနံပါတ် ပို့လိုက်ရင် QR ရပါမယ်။ အသုံးပြုနည်းက /help ။"
    ),
    LANG_ALREADY="✅ {name} ကို ရွေးထားပြီးသားပါ။",
    INLINE_PROMPT="မြန်မာ ဖုန်းနံပါတ် ရိုက်ထည့်ပါ (ဥပမာ 09xxxxxxxxx)",
    INLINE_BAD_NUMBER="မြန်မာ မိုဘိုင်း နံပါတ် မဟုတ်ပါဘူး — Bot ဖွင့်ဖို့ နှိပ်ပါ",
    INLINE_OPEN_BOT="Bot ကို ဖွင့်ပါ",
    COMMAND_START="စတင်ရန် / app ရွေးရန်",
    COMMAND_HELP="အသုံးပြုနည်း",
    COMMAND_LANG="ဘာသာစကား ပြောင်းရန်",
)
# <<<STRINGS>>>

STRINGS: Mapping[Language, Strings] = {Language.EN: EN, Language.MY: MY}


def get(lang: Language | None = None) -> Strings:
    """Strings for ``lang``, falling back to the default rather than raising."""
    return STRINGS.get(lang or DEFAULT_LANGUAGE, STRINGS[DEFAULT_LANGUAGE])
