import { createLanguageController, localeFor } from "./core/i18n.mjs";

function updateDemoDate({ language }) {
  const date = document.querySelector("#demoDate");
  if (!date) return;
  date.textContent = new Date().toLocaleDateString(localeFor(language), {
    weekday: "long",
    day: "numeric",
    month: "long"
  });
}

async function init() {
  const languageController = createLanguageController({ onApplied: updateDemoDate });
  try { await languageController.apply(languageController.language); }
  catch { await languageController.apply("en"); }

  document.querySelectorAll("[data-lang]").forEach((button) => {
    button.addEventListener("click", () => languageController.apply(button.dataset.lang));
  });
}

if (typeof document !== "undefined") {
  window.addEventListener("DOMContentLoaded", init, { once: true });
}
