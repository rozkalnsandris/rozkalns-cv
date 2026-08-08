import { createLanguageController } from "./core/i18n.mjs";
import {
  buildChatPayload,
  createChatController,
  createDialogController,
  normalizeCompletedHistory
} from "./features/chat.mjs";
import { createContactController } from "./features/contact.mjs";
import { createStatsController, REQUIRED_STATS, validateStats } from "./features/stats.mjs";
import { enhanceSkillIcons } from "./ui/icons.mjs";

const PDFS = Object.freeze({
  en: "/cv.pdf",
  de: "/cv-de.pdf",
  lv: "/cv-lv.pdf"
});

export { buildChatPayload, normalizeCompletedHistory, REQUIRED_STATS, validateStats };

function createNavigationObserver() {
  if (!("IntersectionObserver" in window)) return;
  const links = [...document.querySelectorAll(".site-nav a")];
  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      for (const link of links) {
        link.removeAttribute("aria-current");
        if (link.getAttribute("href") === `#${entry.target.id}`) {
          link.setAttribute("aria-current", "true");
        }
      }
    }
  }, { rootMargin: "-30% 0px -60% 0px" });
  document.querySelectorAll("main section[id]").forEach((section) => observer.observe(section));
}

async function init() {
  const languageController = createLanguageController({ pdfs: PDFS });
  try { await languageController.apply(languageController.language); }
  catch { await languageController.apply("en"); }

  document.querySelectorAll("[data-lang]").forEach((button) => {
    button.addEventListener("click", async () => {
      await languageController.apply(button.dataset.lang);
    });
  });

  enhanceSkillIcons();
  createContactController(languageController);

  const stats = createStatsController(languageController);
  stats.start();
  document.addEventListener(
    "visibilitychange",
    () => document.hidden ? stats.stop() : stats.start()
  );

  createDialogController();
  createChatController(languageController);
  createNavigationObserver();
}

if (typeof document !== "undefined") {
  window.addEventListener("DOMContentLoaded", init, { once: true });
}
