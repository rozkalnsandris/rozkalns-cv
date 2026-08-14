export const SUPPORTED_LANGUAGES = Object.freeze(["en", "de", "lv"]);

const TRANSLATIONS = Object.freeze({
  en: new URL("../../content/translations/en.json", import.meta.url).href,
  de: new URL("../../content/translations/de.json", import.meta.url).href,
  lv: new URL("../../content/translations/lv.json", import.meta.url).href
});

const SKILL_LIST_KEYS = Object.freeze({
  skills_core: "skills_core_items",
  skills_working: "skills_working_items",
  skills_learning: "skills_learning_items",
  skills_foundations: "skills_foundations_items"
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

function translationItems(value) {
  if (typeof value !== "string") return null;
  const items = value.split("·").map((item) => item.trim());
  if (!items.length || items.some((item) => !item)) return null;
  return items;
}

export function applySkillTranslations(messages, { root = globalThis.document } = {}) {
  let applied = 0;
  root.querySelectorAll(".skill-row").forEach((row) => {
    const label = row.querySelector("dt[data-i18n]");
    const listKey = SKILL_LIST_KEYS[label?.dataset?.i18n];
    if (!listKey) return;
    const items = translationItems(messages[listKey]);
    if (!items) return;
    const chips = [...row.querySelectorAll(".skill-chip")];
    if (items.length !== chips.length) return;
    chips.forEach((chip, index) => {
      chip.textContent = items[index];
    });
    applied += 1;
  });
  return applied;
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
  applySkillTranslations(messages, { root });
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
