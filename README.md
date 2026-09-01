# Myanmar Pay QR Bot (KBZ Pay & WavePay) 🇲🇲

A fast, lightweight, and modern Telegram bot that converts customer phone numbers into instant, scannable payment QR codes for **KBZ Pay** and **WavePay**.

---

## ✨ Features

- **KBZ Pay Support**: Uses reverse-engineered 42-byte TLV algorithm (BCD-encoded phone, timestamp & checksum) that is directly recognized by the KBZPay app.
- **WavePay Support**: Generates WavePay-compatible payment QR codes.
- **Branded QR Cards**:
  - **KBZ Pay**: Crisp White background with KBZ Brand Blue QR code (`#0066B3`) and accent styling.
  - **WavePay**: Crisp White background with Wave Brand Gold/Yellow QR code (`#D98200`) designed for optimal scanner contrast.
  - Recipient phone number clearly printed below the QR code to easily spot typos.
- **Modern Telegram UX Flow**:
  - Clear English explanation on `/start` without demanding phone numbers upfront.
  - Inline buttons attached to every message bubble for seamless provider switching.
  - Direct message quote-replies to user inputs.
  - FSM in-memory state tracking.
- **Validation**:
  - Automatically cleans dashes, spaces, and formatting characters.
  - Validates Myanmar `09` mobile prefix and 10–11 digit format.
  - Warns on 10-digit legacy numbers.

---

## 📁 Project Structure

```
kbz/qr-bot/
├── bot/
│   ├── __init__.py
│   ├── __main__.py          # Entry point (python -m bot)
│   ├── config.py            # .env / BOT_TOKEN loader & logging setup
│   ├── texts.py             # Message templates & localization strings
│   ├── states.py            # FSM state definitions
│   ├── handlers/
│   │   ├── __init__.py      # Router aggregation
│   │   ├── start.py         # /start command handler (with quote reply)
│   │   ├── provider.py      # Inline button callback handler
│   │   └── phone.py         # Phone input -> Branded QR photo reply
│   ├── keyboards/
│   │   ├── __init__.py
│   │   └── provider_kb.py   # Inline keyboard builder with ✅ active mark
│   └── services/
│       ├── __init__.py
│       ├── providers.py     # Provider enum
│       ├── validators.py    # Phone normalization and validation rules
│       ├── kbzpay_qr.py     # KBZPay TLV QR string generator
│       ├── wavepay_qr.py    # WavePay QR string generator
│       └── renderer.py      # Pillow-based branded QR card generator
├── .env.example
├── .env
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10 or higher
- System font `DejaVuSans-Bold` (standard on Debian/Ubuntu/Linux distributions)

### 2. Installation

1. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### 3. Configuration

1. Get a Telegram Bot token from [@BotFather](https://t.me/BotFather).
2. Open `.env` and paste your bot token:
   ```env
   BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
   LOG_LEVEL=INFO
   ```

### 4. Running the Bot

Run the bot as a module from the project root:
```bash
python3 -m bot
```

The bot runs in asynchronous long polling mode — no webhooks, open ports, or domain certificates required.

Logs will be streamed to the console and automatically saved to `bot.log` (with automatic log rotation up to 2MB).

---

## 🧪 Testing

1. Open your Telegram bot and send `/start`.
2. Click **KBZ Pay** or **WavePay**.
3. Send a test Myanmar phone number: `09***6738` (e.g. `09xxxxxxxxx`)
4. The bot will quote-reply with the custom branded QR image.
5. Scan the QR code with the respective app to verify recipient details.

---

## 🔒 Security & Privacy Notice

- This bot **only generates QR payloads** locally. It does not transfer money or access user bank accounts.
- Always verify the recipient's name on the payment app's confirmation screen before authorizing any transfer.
