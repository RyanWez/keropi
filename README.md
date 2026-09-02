# Keropi — Myanmar Pay QR Bot (KBZ Pay & WavePay) 🇲🇲

A Telegram bot that turns a customer's phone number into a scannable payment QR
code for **KBZ Pay** and **WavePay**, so nobody has to retype a number into a
transfer screen.

Anyone may use it. There is a short per-user cooldown so one person's burst can't
slow it down for everybody else.

---

## ✨ What it does

- **KBZ Pay** — builds the 42-byte TLV payload the KBZPay app accepts (BCD-encoded
  number, timestamp and checksum), reverse-engineered from KBZPay 5.8.5.
- **WavePay** — WavePay reads a bare phone number, so the payload is the number.
- **Branded cards** — white background, KBZ blue (`#0066B3`) or Wave amber
  (`#D98200`) for scanner contrast, with the recipient's number printed underneath
  so a typo is obvious before anyone taps send.
- **Inline mode** — `@yourbot 09xxxxxxxxx` from inside any chat returns both
  providers as pickable results, no need to open the bot first.
- **Repeat numbers are free** — once a card has been sent, Telegram will re-send it
  from its `file_id`, so the same number costs no rendering and no upload.
- **Forgiving input** — `09…`, `+959…`, `959…`, and spaces, dashes or brackets.
- **A way to reach you when it fails** — error replies swap the provider buttons for
  a contact link, since switching provider is not what a stuck user needs.

## 📏 Number formats, and why KBZ Pay is stricter

Myanmar mobile numbers are **9, 10 or 11 digits** in national `09…` form. That
comes from the Posts and Telecommunications Department's numbering plan: the mobile
NDC is `9` and subscriber numbers are 7, 8 or 9 digits. Since 2014 every newly
issued number is 11 digits, but the older 9- and 10-digit ranges were never
withdrawn and are still in service. Anything shorter is a **landline** (`01…`), not
a mobile, and can't receive a wallet transfer.

| Provider | Accepts | Why |
| --- | --- | --- |
| WavePay | 9, 10, 11 digits | The payload is the number verbatim. |
| KBZ Pay | 11 digits only | The QR stores the number in a fixed 6-byte BCD field that exactly 11 digits fill. |

Send KBZ Pay a 10-digit number and it explains the limit and points you at
WavePay rather than producing a QR it can't stand behind. Before this rule existed,
a 10-digit number produced a 41-byte payload, which shifted the trailing template
bytes and made the server read `0996047673` as `099604767326` — a silently wrong
recipient.

Padding shorter numbers to fill the field is implemented, but **off by default**
behind `KBZPAY_ALLOW_SHORT_NUMBERS`. It can't be verified from the app: KBZPay's
*server* builds the payload (there is no BCD encoder in the APK — the base64 body
arrives via `UserInfo.getReceiptQRCode` / `ObtainQRCodeReceipt` and the app only
appends the timestamp suffix), so the server's padding rule is unknown. Turning it
on without a confirmed sample would mean guessing at where money goes.

**If you have a 9- or 10-digit number**, `/decode` settles it — see below.

---

## 📁 Layout

```
keropi/
├── bot/
│   ├── __main__.py                 # entry point: python -m bot
│   ├── config.py                   # env parsing, logging
│   ├── texts.py                    # all user-facing copy, keyed for a future /lang
│   ├── assets/fonts/               # vendored DejaVu, so cards render the same everywhere
│   ├── handlers/
│   │   ├── errors.py               # catch-all error handler
│   │   ├── diagnostics.py          # owner-only /decode
│   │   ├── start.py                # /start, /help, unknown commands
│   │   ├── provider.py             # inline button callbacks
│   │   ├── inline.py               # inline mode
│   │   └── phone.py                # number -> QR card (private chats only)
│   ├── keyboards/provider_kb.py
│   ├── middlewares/
│   │   ├── provider_ctx.py         # resolves the selected provider once per update
│   │   ├── throttle.py             # per-user cooldown
│   │   └── retry_after.py          # honours Telegram's flood-control back-off
│   └── services/
│       ├── providers.py            # Provider enum + tolerant parsing
│       ├── validators.py           # normalisation and length rules
│       ├── kbzpay_qr.py            # TLV payload builder
│       ├── wavepay_qr.py
│       ├── qr_decode.py            # takes a QR back apart (for /decode)
│       ├── renderer.py             # Pillow card renderer
│       ├── render_pool.py          # bounded thread pool for rendering
│       ├── qr_cache.py             # file_id LRU
│       └── db.py                   # per-user settings (SQLite)
├── tests/
├── render.yaml
├── pyproject.toml
└── requirements.txt
```

---

## 🚀 Running it

Python 3.11 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate          # do not skip this — see Troubleshooting
pip install -e ".[dev]"
cp .env.example .env               # then paste your @BotFather token
python -m bot
```

Long polling, so no webhook, domain or certificate is needed. Logs go to the
console and to `bot.log`, rotating at 1 MB with three backups.

### Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `BOT_TOKEN` | *required* | From [@BotFather](https://t.me/BotFather). |
| `LOG_LEVEL` | `INFO` | |
| `PORT` | unset | Starts the health endpoint. Render sets this for you. |
| `DB_PATH` | `bot.db` | Where user preferences live. |
| `OWNER_ID` | unset | Telegram user id allowed to run `/decode`. |
| `QR_CACHE_CHAT_ID` | unset | Chat to upload cards to for inline mode. Unset disables inline mode. |
| `CONTACT_URL` | `https://t.me/Super001z` | Target of the contact button on error replies. Empty drops the button. |
| `KBZPAY_ALLOW_SHORT_NUMBERS` | `false` | Allow 9/10-digit KBZ Pay numbers with unverified padding. |
| `RENDER_WORKERS` | `3` | Threads for card rendering. |
| `MAX_CONCURRENT_UPDATES` | `24` | Ceiling on updates in flight. |
| `THROTTLE_SECONDS` | `2` | Per-user cooldown. |
| `QR_CACHE_SIZE` | `2000` | How many `file_id`s to remember. |

### Enabling inline mode

1. `/setinline` in @BotFather, with a placeholder such as `09xxxxxxxxx`.
2. Create a private channel, add the bot as an admin, and set `QR_CACHE_CHAT_ID` to
   its id (a negative number). Inline results can only reference a URL or a
   `file_id`, never raw bytes, so a card has to be uploaded once before it can be
   offered inline.

---

## 🧪 Tests

```bash
pytest
```

The suite pins the things that must not drift:

- the reverse-engineered template bytes, and that the TLV is **always** 42 bytes —
  the failure mode of a shifted field is a wrong recipient, not an error;
- normalisation and per-provider length rules, including Unicode digits like `²`
  and `٩`, which `str.isdigit()` accepts and the BCD encoder cannot;
- every card is rendered and scanned back with `zxing-cpp`, so a layout change
  can't quietly break scanning;
- the dispatcher end to end: a repeat number reuses its `file_id`, a stale
  `file_id` falls back to rendering, group messages are ignored, and a handler
  that raises still gets a reply out.

---

## 🔧 `/decode` — the open question

KBZPay's payload is built server-side, so the only way to learn how a legacy 9- or
10-digit number is encoded is to look at a real Receive QR from such an account.

Set `OWNER_ID`, then send `/decode` with a photo of any KBZPay Receive QR (or paste
the QR string). It reports the TLV length, whether the templates match, the phone
field's bytes, the digits and pad nibbles, the timestamp and the checksum.

A Receive QR is meant to be shown to strangers, so asking someone with a legacy
number for a screenshot costs nothing and — unlike a test transfer — moves no
money. One sample is enough to either confirm the padding rule and enable
`KBZPAY_ALLOW_SHORT_NUMBERS`, or to show that the format differs.

---

## ☁️ Deploying to Render (free tier)

`render.yaml` describes the service. Keep an external pinger such as UptimeRobot
hitting `/health` every 5 minutes.

Free-tier facts worth knowing, all from Render's own docs:

- **The filesystem is ephemeral, always.** `bot.db` is wiped on every redeploy,
  restart *and* spin-down, and free web services cannot attach a persistent disk.
  That is fine here: losing a saved provider costs one button tap, and losing the
  `file_id` cache costs one re-render. Point `DB_PATH` at a mounted disk, or move
  to a hosted database, if that stops being true.
- **750 instance hours per month, per workspace.** Running 24/7 for a 31-day month
  is ~744 hours, so there is almost no headroom — and the quota is shared. **A
  second always-on free service will exhaust it and suspend both.**
- "Render might restart a Free web service at any time." No schedule is published.
- 512 MB RAM, shared CPU. Spin-down after 15 minutes without inbound traffic; a
  request wakes it in about a minute. Don't point the pinger at `/robots.txt` —
  Render answers that itself without waking the instance.

### Capacity, roughly

Telegram allows a bot about 30 messages per second overall, so a QR per message
puts the ceiling near 100,000 per hour. A thousand users sending ten numbers a day
averages about 0.12 per second, so the limit was never throughput — it was that
rendering blocked the event loop and made concurrent users queue. Rendering now
runs in a small thread pool, in-flight updates are capped, and repeat numbers skip
rendering entirely.

---

## 🩺 Troubleshooting

**`ModuleNotFoundError: No module named 'aiogram'`** — the virtualenv isn't active.
A shell prompt showing a Python version (starship's `via 🐍`) does *not* mean the
venv is active; check `echo $VIRTUAL_ENV`. Either `source .venv/bin/activate` first,
or run `.venv/bin/python -m bot` directly.

---

## 🔒 Security & privacy

- Everything is generated locally. The bot moves no money and touches no bank
  account.
- It cannot tell whether an account exists. **Always check the recipient's name on
  the payment app's confirmation screen before authorising a transfer** — that name
  is the last safety net against a mistyped number.
- Sharing a QR reveals the account number in it, but the only thing a stranger can
  do with that is send money *to* it.
- `/decode` is owner-gated: its reports expose a recipient's number, and ungated it
  would amount to a phone-number lookup tool.
- This exists to cut typos in transfers. Please don't use it for anything else.
