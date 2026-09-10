"use strict";

const copy = {
  en: {
    eyebrow: "PAYMENT, MADE EASIER",
    title: "Turn a phone number into a payment QR.",
    subtitle: "Create a clean, scan-ready card for KBZ Pay or WavePay — without retyping the recipient's number.",
    local: "Generated privately",
    noHistory: "No number history",
    step: "QUICK GENERATOR",
    generatorTitle: "Create your QR card",
    private: "Private",
    chooseProvider: "Choose a provider",
    kbzHint: "11-digit numbers",
    waveHint: "9–11 digit numbers",
    phoneLabel: "Recipient's phone number",
    phoneHint: "Formats like 09…, +959… and spaces or dashes are accepted.",
    clear: "Clear",
    clearPhone: "Clear phone number",
    addAmount: "Add amount (optional)",
    removeAmount: "Remove amount",
    amountLabel: "Amount (MMK)",
    amountHint: "Whole kyat only. Leave blank to let the sender enter it.",
    amountNotice: "Experimental: verify the recipient and amount in KBZ Pay before sending.",
    generate: "Generate QR card",
    readyLabel: "READY TO SCAN",
    readyTitle: "Your QR card is ready",
    download: "Download PNG",
    share: "Share",
    safetyTitle: "Check before you send",
    safetyCopy: "Always verify the recipient name in the payment app. Keropi cannot confirm whether an account exists.",
    footer: "Keropi creates QR images only. It never moves or stores your money.",
    generating: "Creating your QR card…",
    done: "QR card created.",
    networkError: "We could not reach the generator. Please try again.",
    shareText: "Payment QR card created with Keropi",
    copied: "Sharing is not supported here. The QR card was downloaded instead.",
    previewAlt: "Generated payment QR card",
    closePreview: "Close preview",
  },
  my: {
    eyebrow: "ငွေလွှဲမှုကို ပိုမိုလွယ်ကူစေသည်",
    title: "ဖုန်းနံပါတ်မှ ငွေလွှဲ QR ပြုလုပ်ပါ။",
    subtitle: "လက်ခံသူ၏ နံပါတ်ကို ပြန်ရိုက်စရာမလိုဘဲ KBZ Pay သို့မဟုတ် WavePay အတွက် Scan ဖတ်နိုင်သော QR Card ပြုလုပ်ပါ။",
    local: "လုံခြုံစွာ ပြုလုပ်သည်",
    noHistory: "နံပါတ်မှတ်တမ်း မသိမ်းပါ",
    step: "အမြန် QR ပြုလုပ်ရန်",
    generatorTitle: "သင့် QR Card ကို ပြုလုပ်ပါ",
    private: "လုံခြုံမှုရှိ",
    chooseProvider: "အသုံးပြုမည့် Pay ကို ရွေးပါ",
    kbzHint: "ဂဏန်း ၁၁ လုံး",
    waveHint: "ဂဏန်း ၉ မှ ၁၁ လုံး",
    phoneLabel: "လက်ခံသူ၏ ဖုန်းနံပါတ်",
    phoneHint: "09…၊ +959…၊ space နှင့် dash ပါသော နံပါတ်များကို လက်ခံပါသည်။",
    clear: "ရှင်းမည်",
    clearPhone: "ဖုန်းနံပါတ် ရှင်းမည်",
    addAmount: "ငွေပမာဏ ထည့်မည် (မထည့်လည်း ရပါသည်)",
    removeAmount: "ငွေပမာဏ မထည့်တော့ပါ",
    amountLabel: "ငွေပမာဏ (ကျပ်)",
    amountHint: "ကျပ်ပြည့်သာ ထည့်ပါ။ လွှဲသူက ထည့်စေလိုပါက မဖြည့်ဘဲထားပါ။",
    amountNotice: "စမ်းသပ်ဆဲ — ငွေမလွှဲမီ KBZ Pay ထဲရှိ လက်ခံသူနှင့် ပမာဏကို စစ်ပါ။",
    generate: "QR Card ပြုလုပ်မည်",
    readyLabel: "SCAN ဖတ်ရန် အသင့်ဖြစ်ပါပြီ",
    readyTitle: "သင့် QR Card အဆင်သင့်ဖြစ်ပါပြီ",
    download: "PNG သိမ်းမည်",
    share: "မျှဝေမည်",
    safetyTitle: "မလွှဲမီ စစ်ဆေးပါ",
    safetyCopy: "Payment App ထဲရှိ လက်ခံသူအမည်ကို အမြဲစစ်ဆေးပါ။ Keropi သည် အကောင့်ရှိ၊ မရှိကို အတည်မပြုနိုင်ပါ။",
    footer: "Keropi သည် QR ပုံသာ ပြုလုပ်ပေးပြီး ငွေကို လွှဲပြောင်းခြင်း သို့မဟုတ် သိမ်းဆည်းခြင်း မပြုပါ။",
    generating: "QR Card ပြုလုပ်နေပါသည်…",
    done: "QR Card ပြုလုပ်ပြီးပါပြီ။",
    networkError: "QR စနစ်နှင့် မချိတ်ဆက်နိုင်ပါ။ ထပ်စမ်းကြည့်ပါ။",
    shareText: "Keropi ဖြင့် ပြုလုပ်ထားသော ငွေလွှဲ QR Card",
    copied: "ဤ Browser တွင် မျှဝေ၍ မရသဖြင့် QR Card ကို Download လုပ်ပေးလိုက်ပါသည်။",
    previewAlt: "ပြုလုပ်ထားသော ငွေလွှဲ QR Card",
    closePreview: "Preview ပိတ်မည်",
  },
};

const telegramApp = window.Telegram?.WebApp ?? null;

const form = document.querySelector("#qr-form");
const phoneInput = document.querySelector("#phone");
const clearPhoneButton = document.querySelector("#clear-phone");
const amountSection = document.querySelector("#amount-section");
const amountToggle = document.querySelector("#amount-toggle");
const amountToggleLabel = amountToggle.querySelector("[data-i18n]");
const amountToggleIcon = amountToggle.querySelector(".amount-toggle-icon");
const amountPanel = document.querySelector("#amount-panel");
const amountInput = document.querySelector("#amount");
const clearAmountButton = document.querySelector("#clear-amount");
const generateButton = document.querySelector("#generate-button");
const formStatus = document.querySelector("#form-status");
const resultCard = document.querySelector("#result-card");
const preview = document.querySelector("#qr-preview");
const normalizedPhone = document.querySelector("#normalized-phone");
const downloadButton = document.querySelector("#download-button");
const shareButton = document.querySelector("#share-button");
const closeResult = document.querySelector("#close-result");

let language = readPreference("keropi-language", "") || telegramLanguageHint() || "en";
let amountExpanded = false;
let imageBlob = null;
let imageUrl = null;
let filename = "keropi-payment-qr.png";

function readPreference(key, fallback) {
  try {
    return window.localStorage.getItem(key) || fallback;
  } catch {
    return fallback;
  }
}

function storePreference(key, value) {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // Preferences are optional when storage is unavailable.
  }
}

function telegramLanguageHint() {
  // initDataUnsafe is only ever read here, and only for the client language,
  // as a presentation hint for first-time visitors. No identity data leaves
  // the page or reaches storage.
  const code = telegramApp?.initDataUnsafe?.user?.language_code;
  if (typeof code !== "string") return null;
  const primary = code.toLowerCase().split(/[-_]/, 1)[0];
  return copy[primary] ? primary : null;
}

function setLanguage(nextLanguage, persist = true) {
  language = copy[nextLanguage] ? nextLanguage : "en";
  document.documentElement.lang = language;
  document.querySelectorAll("[data-i18n]").forEach((element) => {
    element.textContent = copy[language][element.dataset.i18n];
  });
  document.querySelectorAll("[data-language]").forEach((button) => {
    const active = button.dataset.language === language;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  document.querySelectorAll("[data-i18n-aria-label]").forEach((element) => {
    element.setAttribute(
      "aria-label",
      copy[language][element.dataset.i18nAriaLabel],
    );
  });
  preview.alt = copy[language].previewAlt;
  closeResult.setAttribute("aria-label", copy[language].closePreview);
  updateAmountControls();
  if (persist) storePreference("keropi-language", language);
}

function selectedProvider() {
  return form.querySelector('input[name="provider"]:checked')?.value || "kbzpay";
}

function setAmountExpanded(expanded) {
  amountExpanded = expanded;
  amountPanel.hidden = !expanded;
  amountToggle.setAttribute("aria-expanded", String(expanded));
  amountToggleIcon.textContent = expanded ? "−" : "+";
  updateAmountControls();
  if (expanded) amountInput.focus();
}

function updateAmountControls() {
  const supportsAmount = selectedProvider() === "kbzpay";
  amountSection.hidden = !supportsAmount;
  amountInput.disabled = !supportsAmount;
  amountToggleLabel.textContent = copy[language][
    amountExpanded ? "removeAmount" : "addAmount"
  ];
}

function setLoading(isLoading) {
  generateButton.disabled = isLoading;
  generateButton.classList.toggle("is-loading", isLoading);
  phoneInput.setAttribute("aria-busy", String(isLoading));
}

function updateClearPhoneButton() {
  clearPhoneButton.hidden = phoneInput.value.length === 0;
}

function formatAmountInput() {
  const compact = amountInput.value.replaceAll(",", "");
  if (!/^\d*$/.test(compact)) return;
  amountInput.value = compact.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

function setStatus(message, success = false) {
  formStatus.textContent = message;
  formStatus.classList.toggle("is-success", success);
}

function clearResult() {
  resultCard.hidden = true;
  preview.removeAttribute("src");
  normalizedPhone.textContent = "";
  if (imageUrl) URL.revokeObjectURL(imageUrl);
  imageUrl = null;
  imageBlob = null;
}

function downloadImage() {
  if (!imageBlob || !imageUrl) return;
  const link = document.createElement("a");
  link.href = imageUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
}

async function generateQr(event) {
  event.preventDefault();
  const provider = selectedProvider();
  const amount = provider === "kbzpay" && amountExpanded ? amountInput.value : "";
  storePreference("keropi-provider", provider);
  setLoading(true);
  setStatus(copy[language].generating);

  try {
    const response = await fetch("/api/qr", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "image/png, application/json" },
      body: JSON.stringify({ provider, phone: phoneInput.value, amount, language }),
    });

    if (!response.ok) {
      let message = copy[language].networkError;
      try {
        const payload = await response.json();
        message = payload?.error?.message || message;
      } catch {
        // Keep the generic message for non-JSON server errors.
      }
      clearResult();
      setStatus(message);
      phoneInput.focus();
      return;
    }

    clearResult();
    imageBlob = await response.blob();
    imageUrl = URL.createObjectURL(imageBlob);
    filename = contentFilename(response.headers.get("Content-Disposition"), provider);
    preview.src = imageUrl;
    normalizedPhone.textContent = response.headers.get("X-Normalized-Phone") || "";
    resultCard.hidden = false;
    setStatus(copy[language].done, true);
    resultCard.scrollIntoView({ behavior: "smooth", block: "center" });
  } catch {
    clearResult();
    setStatus(copy[language].networkError);
  } finally {
    setLoading(false);
  }
}

function contentFilename(header, provider) {
  const match = header?.match(/filename="([a-z0-9_.-]+)"/i);
  return match ? match[1] : `${provider}_payment_qr.png`;
}

async function shareImage() {
  if (!imageBlob) return;
  const file = new File([imageBlob], filename, { type: "image/png" });
  if (navigator.share && (!navigator.canShare || navigator.canShare({ files: [file] }))) {
    try {
      await navigator.share({ title: "Keropi Pay QR", text: copy[language].shareText, files: [file] });
      return;
    } catch (error) {
      if (error.name === "AbortError") return;
    }
  }
  downloadImage();
  setStatus(copy[language].copied, true);
}

function setTelegramVariable(name, value) {
  if (value !== null && value !== undefined) {
    document.documentElement.style.setProperty(name, value);
  }
}

function telegramSupports(version) {
  return typeof telegramApp?.isVersionAtLeast === "function"
    && telegramApp.isVersionAtLeast(version);
}

function applyTelegramTheme() {
  if (!telegramApp) return;
  setTelegramVariable("color-scheme", telegramApp.colorScheme === "dark" ? "dark" : "light");
  const theme = telegramApp.themeParams ?? {};
  const accents = {
    "--ink": theme.text_color,
    "--muted": theme.hint_color,
    "--canvas": theme.bg_color,
    "--surface": theme.secondary_bg_color ?? theme.section_bg_color,
    "--green": theme.button_color,
    "--green-dark": theme.button_color,
  };
  for (const [property, value] of Object.entries(accents)) {
    if (typeof value === "string") setTelegramVariable(property, value);
  }
  const themeColor = document.querySelector('meta[name="theme-color"]');
  if (themeColor && typeof theme.bg_color === "string") {
    themeColor.setAttribute("content", theme.bg_color);
  }
  // Both methods arrived in Bot API 6.1. Older desktop clients log warnings
  // instead of ignoring unsupported calls quietly, so gate them explicitly.
  if (telegramSupports("6.1")) {
    telegramApp.setHeaderColor?.(theme.header_bg_color ?? "bg_color");
    telegramApp.setBackgroundColor?.(theme.bg_color ?? "bg_color");
  }
}

function syncTelegramViewport() {
  if (!telegramApp) return;
  const height = telegramApp.viewportHeight ?? telegramApp.screenHeight;
  if (Number.isFinite(height)) {
    setTelegramVariable("--telegram-viewport-height", `${height}px`);
  }
}

function syncTelegramInsets() {
  if (!telegramApp) return;
  // Prefer the content safe area; fall back to the plain safe area. Both are
  // combined with env() in CSS so non-Telegram browsers keep working.
  const insets = telegramApp.contentSafeAreaInset ?? telegramApp.safeAreaInset;
  if (!insets) return;
  for (const side of ["top", "right", "bottom", "left"]) {
    if (Number.isFinite(insets[side])) {
      setTelegramVariable(`--telegram-safe-inset-${side}`, `${insets[side]}px`);
    }
  }
}

function initTelegramApp() {
  if (!telegramApp) return; // Plain browser: the CSS fallbacks apply unchanged.
  document.documentElement.classList.add("is-telegram-app");
  applyTelegramTheme();
  syncTelegramViewport();
  syncTelegramInsets();
  telegramApp.onEvent?.("themeChanged", applyTelegramTheme);
  telegramApp.onEvent?.("viewportChanged", syncTelegramViewport);
  telegramApp.onEvent?.("safeAreaChanged", syncTelegramInsets);
  telegramApp.onEvent?.("contentSafeAreaChanged", syncTelegramInsets);
  telegramApp.ready();
  telegramApp.expand();
}

form.addEventListener("submit", generateQr);
phoneInput.addEventListener("input", updateClearPhoneButton);
clearPhoneButton.addEventListener("click", () => {
  phoneInput.value = "";
  updateClearPhoneButton();
  clearResult();
  setStatus("");
  setAmountExpanded(false);
  phoneInput.focus();
});
amountToggle.addEventListener("click", () => setAmountExpanded(!amountExpanded));
amountInput.addEventListener("input", formatAmountInput);
clearAmountButton.addEventListener("click", () => {
  amountInput.value = "";
  amountInput.focus();
});
downloadButton.addEventListener("click", downloadImage);
shareButton.addEventListener("click", shareImage);
closeResult.addEventListener("click", () => {
  clearResult();
  phoneInput.focus();
});

document.querySelectorAll("[data-language]").forEach((button) => {
  button.addEventListener("click", () => setLanguage(button.dataset.language));
});

document.querySelectorAll('input[name="provider"]').forEach((radio) => {
  radio.addEventListener("change", () => {
    storePreference("keropi-provider", radio.value);
    updateAmountControls();
    clearResult();
    setStatus("");
  });
});

const savedProvider = readPreference("keropi-provider", "kbzpay");
const savedProviderInput = document.querySelector(`input[name="provider"][value="${savedProvider}"]`);
if (savedProviderInput) savedProviderInput.checked = true;
if (!navigator.share) shareButton.hidden = true;
updateClearPhoneButton();
setLanguage(language, false);
initTelegramApp();
