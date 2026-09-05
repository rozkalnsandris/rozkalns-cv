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

export function regionDisplayName(region, language, { DisplayNames = globalThis.Intl?.DisplayNames } = {}) {
  const code = String(region || "").trim().toUpperCase();
  if (!/^[A-Z]{2}$/.test(code)) return code;
  if (typeof DisplayNames !== "function") return code;
  try {
    return new DisplayNames([localeFor(language)], {
      type: "region",
      fallback: "code"
    }).of(code) || code;
  } catch {
    return code;
  }
}

export function applyRegionDisplayNames(language, {
  root = globalThis.document,
  DisplayNames = globalThis.Intl?.DisplayNames
} = {}) {
  root.querySelectorAll("[data-region-code]").forEach((element) => {
    const city = String(element.dataset.city || "").trim();
    const region = String(element.dataset.regionCode || "").trim().toUpperCase();
    if (!city || !/^[A-Z]{2}$/.test(region)) return;
    element.textContent = `${city}, ${regionDisplayName(region, language, { DisplayNames })}`;
  });
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

function webMessage(messages, key) {
  const override = messages[`web_${key}`];
  return typeof override === "string" ? override : messages[key];
}

function translationItems(value) {
  if (typeof value !== "string") return null;
  const items = value.split("Â·").map((item) => item.trim());
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
      const icon = chip.querySelector("svg");
      chip.textContent = items[index];
      if (icon) chip.prepend(icon);
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
  applyRegionDisplayNames(safe, { root });
  root.querySelectorAll("[data-i18n]").forEach((element) => {
    const value = webMessage(messages, element.dataset.i18n);
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
  root.querySelectorAll("[data-lang]").forEach((control) => {
    const selected = control.dataset.lang === safe;
    if (String(control.tagName || "").toUpperCase() === "A") {
      control.removeAttribute("aria-pressed");
      if (selected) control.setAttribute("aria-current", "page");
      else control.removeAttribute("aria-current");
    } else {
      control.removeAttribute("aria-current");
      control.setAttribute("aria-pressed", String(selected));
    }
  });
  if (pdfs) {
    const pdf = root.querySelector(HÜ“[šÈŠNÂˆYˆ
ˆ	‰ˆ\[ÙˆœÖÜØY™WHOOHœİš[™ÈŠH‹œÙ]]šX]Jš™Yˆ‹œÖÜØY™WJNÂˆBˆHÈİÜ˜YÙOËœÙ]][OËŠ˜İ›[™È‹ØY™JNÈHØ]ÚßBˆ™]\›ˆØY™NÂŸB‚™^Ü[˜İ[ÛˆÜ™X]S[™İXYÙPÛÛ›Û\ŠÂˆ›ÛİHÛØ˜[\Ë™Øİ[Y[ˆİÜ˜YÙHHÛØ˜[\Ë›ØØ[İÜ˜YÙKˆ˜]šYØ]Ü“ZÙHHÛØ˜[\Ë›˜]šYØ]Ü‹ˆ™]Ú[\HÛØ˜[\Ë™™]ÚˆœÈH[ˆÛ\YYH[ˆ[š]X[[™İXYÙHH[ŸHHßJHÂˆ][™İXYÙHH[š]X[[™İXYÙHOOH[ˆÈ™Y™\œ™Y[™İXYÙJÈİÜ˜YÙK˜]šYØ]Ü“ZÙHJBˆˆ›Ü›X[^™S[™İXYÙJ[š]X[[™İXYÙJNÂˆ]Y\ÜØYÙ\ÈH[Âˆ]]\İ™\]Y\İHÂ‚ˆ\Ş[˜È[˜İ[Ûˆ\J™^[™İXYÙJHÂˆÛÛœİ™\]Y\İH
ÊÛ]\İ™\]Y\İÂˆÛÛœİØYYH]ØZ]ØYY\ÜØYÙ\Ê™^[™İXYÙKÈ™]Ú[\JNÂˆYˆ
™\]Y\İOOH]\İ™\]Y\İ
H™]\›ˆY\ÜØYÙ\ÎÂˆ[™İXYÙHH\U˜[œÛ][ÛœÊØYY›Y\ÜØYÙ\ËØYY›[™İXYÙKÈ›ÛİİÜ˜YÙKœÈJNÂˆY\ÜØYÙ\ÈHØYY›Y\ÜØYÙ\ÎÂˆÛ\YYËŠÈ[™İXYÙKY\ÜØYÙ\ÈJNÂˆ™]\›ˆY\ÜØYÙ\ÎÂˆB‚ˆ\Ş[˜È[˜İ[ÛˆP\J™^[™İXYÙJHÂˆHÂˆ]ØZ]\J™^[™İXYÙJNÂˆ™]\›ˆYNÂˆHØ]ÚÂˆ™]\›ˆ˜[ÙNÂˆBˆB‚ˆ™]\›ˆÂˆ\KˆP\KˆÙ][™İXYÙJ
HÈ™]\›ˆ[™İXYÙNÈKˆÙ]Y\ÜØYÙ\Ê
HÈ™]\›ˆY\ÜØYÙ\ÎÈBˆNÂŸB