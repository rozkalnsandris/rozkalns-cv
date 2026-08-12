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
  const preferredApplied = await languageController.tryApply(languageController.language);
  if (!preferredApplied) await languageController.tryApply("en");

  document.querySelectorAll("[data-lang]").forEach((button) => {
    button.addEventListener("click", () => {
      void languageController.tryApply(button.dataset.lang);
    });
  });
}

if (typeof document !== "undefined") {
  window.addEventListener("DOMContentLoaded", init, { once: true });
}
