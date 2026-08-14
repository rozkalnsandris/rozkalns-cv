import { createLanguageController, localeFor } from "./core/i18n.mjs";

function updateDemoPage({ language, messages }) {
  const title = messages?.smart_demo;
  if (typeof title === "string" && title) {
    document.title = `${title} · Andris Rožkalns`;
  }

  const date = document.querySelector("#demoDate");
  if (!date) return;
  date.textContent = new Date().toLocaleDateString(localeFor(language), {
    weekday: "long",
    day: "numeric",
    month: "long"
  });
}

async function init() {
  const languageController = createLanguageController({ onApplied: updateDemoPage });
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
