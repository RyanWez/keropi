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
        "(e.g. <code>09***6738</code>) and I'll return the QR."
    ),
    "wavepay": (
        "📱 <b>WavePay</b> selected.\n\n"
        "Now send the customer's phone number "
        "(e.g. <code>09***6738</code>) and I'll return the QR."
    ),
}

NO_PROVIDER = "Please choose a provider first. 👇"

QR_CAPTION = (
    "📷 Scan this with <b>{label}</b>\n"
    "Number: <code>{phone}</code>\n\n"
    "⚠️ Always check the recipient's name on the confirmation screen before sending money."
)

LEGACY_WARNING = "10-digit numbers are not fully verified yet — double-check!"
