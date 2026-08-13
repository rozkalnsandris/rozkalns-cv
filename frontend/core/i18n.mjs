export const SUPPORTED_LANGUAGES = Object.freeze(["en", "de", "lv"]);

const TRANSLATIONS = Object.freeze({
  en: new URL("../../content/translations/en.json", import.meta.url).href,
  de: new URL("../../content/translations/de.json", import.meta.url).href,
  lv: new URL("../../content/translations/lv.json", import.meta.url).href
});

export function normalizeLanguage(value) {
  const candidate = String(value || "").slice(0, 2).toLowerCase();
  return Object.hasOwn(TRANSLATIONS, candidate) ? candidate : "en";
}

export function localeFor(language) {
  const safe = normalizeLanguage(language);
  return safe === "de" ? "de-DE" : safe === "lv" ? "lv-LV" : "en-GB";
}

export function preferredLanguage({ storage = globalThis.localStorage, navigatorLike = globalThis.navigator } = {}) {
  try {
    const saved = storage?.getItem?.("cvlang");
    if (saved && Object.hasOwn(TRANSLATIONS, saved)) return saved;
  } catch {}
  return normalizeLanguage(navigatorLike?.language || "en");
}

export async function loadMessages(language, { fetchImpl = globalThis.fetch } = {}) {
  const safe = normalizeLanguage(language);
  const response = await fetchImpl(TRANSLATIONS[safe], { cache: "force-cache" });
  if (!response.ok) throw new Error("translation unavailable");
  const data = await response.json();
  if (!data || typeof data !== "object" || Array.isArray(data)) {
    throw new Error("translation invalid");
  }
  return { language: safe, messages: data };
}

export function applyTranslations(messages, language, {
  root = globalThis.document,
  storage = globalThis.localStorage,
  pdfs = null
} = {}) {
  const safe = normalizeLanguage(language);
  root.documentElement.lang = safe;
  root.querySelectorAll("[data-i18n]").forEach((element) => {
    const value = messages[element.dataset.i18n];
    if (typeof value === "string") element.textContent = value;
  });
  root.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
    const value = messages[element.dataset.i18nPlaceholder];
    if (typeof value === "string") element.setAttribute("placeholder", value);
  });
  root.querySelectorAll("[data-i18n-label]").forEach((element) => {
    const value = messages[element.dataset.i18nLabel];
    if (typeof value === "string") element.setAttribute("aria-label", value);
  });
  root.querySelectorAll("[data-lang]").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.lang === safe));
  });
  if (pdfs) {
    const pdf = root.querySelector("#pdfLink");
    if (pdf && typeof pdfs[safe] === "string") pdf.setAttribute("href", pdfs[safe]);
  }
  try { storage?.setItem?.("cvlang", safe); } catch {}
  return safe;
}

export function createLanguageController({
  root = globalThis.document,
  storage = globalThis.localStorage,
  navigatorLike = globalThis.navigator,
  fetchImpl = globalThis.fetch,
  pdfs = null,
  onApplied = null
} = {}) {
  let language = preferredLanguage({ storage, navigatorLike });
  let messages = null;
  let latestRequest = 0;

  async function apply(nextLanguage) {
    const request = ++latestRequest;
    const loaded = await loadMessages(nextLanguage, { fetchImpl });
    if (request !== latestRequest) return messages;
    language = applyTranslations(loaded.messages, loaded.language, { root, storage, pdfs });
    messages = loaded.messages;
    onApplied?.({ language, messages });
    return messages;
  }

  async function tryApply(nextLanguage) {
    try {
      await apply(nextLanguage);
      return true;
    } catch {
      return false;
    }
  }

  return {
    apply,
    tryApply,
    get language() { return language; },
    get messages() { return messages; }
  };
}
