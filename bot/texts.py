"""User-facing copy.

Kept in one module so a `/lang` switch can later swap the whole table. Error text
is keyed by ``Reason`` rather than produced inside the validator.
"""

from bot.services.validators import PhoneCheck, Reason

WELCOME = (
    "👋 <b>Pay QR Generator</b>\n\n"
    "Send me a customer's phone number and I will turn it into a "
    "payment QR code you can scan — so you never have to type the "
    "number into the transfer screen again.\n\n"
    "✅ <b>KBZ Pay</b> — KBZPay-ready QR\n"
    "✅ <b>WavePay</b> — WavePay-ready QR\n\n"
    "Pick a provider below to get started. 👇"
)

ASK_PHONE = {
    "kbzpay": (
        "📱 <b>KBZ Pay</b> selected.\n\n"
        "Now send the customer's phone number "
        "(e.g. <code>09xxxxxxxxx</code>) and I'll return the QR."
    ),
    "wavepay": (
        "📱 <b>WavePay</b> selected.\n\n"
        "Now send the customer's phone number "
        "(e.g. <code>09xxxxxxxxx</code>) and I'll return the QR."
    ),
}

NO_PROVIDER = "Please choose a provider first. 👇"

NOT_TEXT = (
    "Please send the phone number as text (e.g. <code>09xxxxxxxxx</code>)."
)

UNKNOWN_COMMAND = (
    "I don't know that command. Use /start to pick a provider or /help for instructions."
)

ERROR_REPLY = (
    "😕 Something went wrong on my side and I couldn't build that QR.\n"
    "Please try again — if it keeps happening, send /start to reset."
)

ERROR_ALERT = "Something went wrong. Please try again."

INLINE_PROMPT = "Type a Myanmar mobile number, e.g. 09xxxxxxxxx"
INLINE_BAD_NUMBER = "Not a Myanmar mobile number — tap to open the bot"
INLINE_OPEN_BOT = "Open the bot"

QR_CAPTION = (
    "📷 Scan with <b>{label}</b>\n"
    "Number: <code>{phone}</code>\n\n"
    "⚠️ Verify recipient name before sending.\n"
    "<i>Note: This bot does not check if the account exists. Please verify recipient details yourself.</i>"
)

#: Printed on the card itself when the QR relies on unverified short-number padding.
PADDING_WARNING = "UNVERIFIED short-number format — check the name!"

HELP = (
    "📖 <b>How to use Pay QR Generator</b>\n\n"
    "1️⃣ Choose your payment provider: <b>KBZ Pay</b> or <b>WavePay</b>.\n"
    "2️⃣ Send the recipient's Myanmar mobile number (e.g. <code>09xxxxxxxxx</code>).\n"
    "3️⃣ The bot will instantly return a branded, high-resolution QR card.\n"
    "4️⃣ Open your KBZPay or WavePay app and scan the QR code to transfer directly without typing the number.\n\n"
    "<b>Number formats</b>\n"
    "• <code>09xxxxxxxxx</code>, <code>+959xxxxxxxxx</code> and <code>959xxxxxxxxx</code> all work — "
    "spaces, dashes and brackets are cleaned up for you.\n"
    "• <b>KBZ Pay</b> needs an 11-digit number. Its QR stores the number in a fixed-width "
    "field that only 11 digits fill exactly.\n"
    "• <b>WavePay</b> also accepts the older 9- and 10-digit numbers.\n\n"
    "💡 You can switch providers anytime using the inline buttons below.\n"
    "⏱ There is a short cooldown between requests so the bot stays responsive for everyone."
)

_PHONE_ERRORS = {
    Reason.EMPTY: (
        "Please send a Myanmar mobile number, e.g. <code>09xxxxxxxxx</code>."
    ),
    Reason.NOT_DIGITS: (
        "⚠️ Numbers only, please. Letters and symbols aren't allowed.\n"
        "Example: <code>09xxxxxxxxx</code>"
    ),
    Reason.NOT_MYANMAR_MOBILE: (
        "⚠️ That doesn't look like a Myanmar mobile number ({digits} digits).\n\n"
        "Mobile numbers start with <code>09</code> and are 9, 10 or 11 digits long — "
        "for example <code>09xxxxxxxxx</code>. "
        "<code>+959…</code> and <code>959…</code> are fine too.\n"
        "Numbers starting <code>01</code> are landlines and can't receive a wallet transfer."
    ),
    Reason.KBZPAY_NEEDS_11: (
        "⚠️ <b>KBZ Pay needs an 11-digit number.</b> You sent {digits} digits.\n\n"
        "KBZPay's QR stores the number in a fixed-width field that only 11 digits fill "
        "exactly, so I can't build a reliable QR for a shorter one — a wrong QR could "
        "point at someone else's account.\n\n"
        "Myanmar still has older 9- and 10-digit numbers, so this may well be genuine. "
        "Two options:\n"
        "• Ask the recipient for their 11-digit number, or\n"
        "• Switch to <b>WavePay</b> below — it accepts this length."
    ),
}


def phone_error(check: PhoneCheck) -> str:
    template = _PHONE_ERRORS.get(check.reason) or _PHONE_ERRORS[Reason.EMPTY]
    return template.format(digits=check.digits)
