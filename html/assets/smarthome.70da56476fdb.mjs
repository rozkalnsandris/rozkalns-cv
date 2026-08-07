const TRANSLATIONS = Object.freeze({
  en: "/i18n/en.f5b04cdd45df.json",
  de: "/i18n/de.3313b3cef4b0.json",
  lv: "/i18n/lv.788ab6598ca4.json"
});

function preferredLanguage() {
  try {
    const saved = localStorage.getItem("cvlang");
    if (saved && TRANSLATIONS[saved]) return saved;
  } catch {}
  const candidate = (navigator.language || "en").slice(0, 2).toLowerCase();
  return TRANSLATIONS[candidate] ? candidate : "en";
}

async function applyLanguage(language) {
  const safe = TRANSLATIONS[language] ? language : "en";
  const response = await fetch(TRANSLATIONS[safe], { cache: "force-cache" });
  if (!response.ok) throw new Error("translation unavailable");
  const data = await response.json();
  document.documentElement.lang = safe;
  document.querySelectorAll("[data-i18n]").forEach((element) => {
    const value = data[element.dataset.i18n];
    if (typeof value === "string") element.textContent = value;
  });
  document.querySelectorAll("[data-lang]").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.lang === safe));
  });
  const date = document.querySelector("#demoDate");
  if (date) {
    date.textContent = new Date().toLocaleDateString(
      safe === "de" ? "de-DE" : safe === "lv" ? "lv-LV" : "en-GB",
      { weekday: "long", day: "numeric", month: "long" }
    );
  }
  try { localStorage.setItem("cvlang", safe); } catch {}
}

async function init() {
  try { await applyLanguage(preferredLanguage()); }
  catch { await applyLanguage("en"); }
  document.querySelectorAll("[data-lang]").forEach((button) => {
    button.addEventListener("click", () => applyLanguage(button.dataset.lang));
  });
}

if (typeof document !== "undefined") {
  window.addEventListener("DOMContentLoaded", init, { once: true });
}
