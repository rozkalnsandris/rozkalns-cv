import { createLanguageController } from "./core/i18n.mjs";
import {
  bindStatsVisibility,
  createStatsController,
  REQUIRED_STATS,
  validateStats
} from "./features/stats.mjs";
import { enhanceSkillIcons } from "./ui/icons.mjs";

const PDFS = Object.freeze({
  en: "/cv.pdf",
  de: "/cv-de.pdf",
  lv: "/cv-lv.pdf"
});

export { REQUIRED_STATS, validateStats };

export function updateMainDocumentTitle({ messages }, { documentLike = globalThis.document } = {}) {
  const role = messages?.role;
  if (!documentLike || typeof role !== "string" || !role.startsWith("Junior ")) return false;
  const titleRole = role.slice("Junior ".length).trim();
  if (!titleRole) return false;
  documentLike.title = `Andris Rožkalns · ${titleRole}`;
  return true;
}

export function installPreloadErrorRecovery(windowLike = globalThis.window) {
  if (
    typeof windowLike?.addEventListener !== "function" ||
    typeof windowLike?.location?.reload !== "function"
  ) {
    return null;
  }

  let reloadRequested = false;
  function recover(event) {
    event?.preventDefault?.();
    if (reloadRequested) return false;
    reloadRequested = true;
    windowLike.location.reload();
    return true;
  }

  windowLike.addEventListener("vite:preloadError", recover);
  return recover;
}

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

function installLazyContact(languageController) {
  const button = document.querySelector("#contactReveal");
  if (!button) return null;
  button.hidden = false;
  let loading = null;

  async function activate() {
    if (loading) return loading;
    loading = import("./features/contact.mjs")
      .then(({ createContactController }) => {
        const controller = createContactController(languageController);
        if (!controller) throw new Error("contact controls unavailable");
        button.removeEventListener("click", activate);
        return controller.start();
      })
      .catch(() => {
        loading = null;
        const status = document.querySelector("#contactVerifyStatus");
        if (status) {
          status.textContent = languageController.messages?.contact_unavailable || "";
          status.dataset.state = "error";
        }
        return null;
      });
    return loading;
  }

  button.addEventListener("click", activate);
  return activate;
}

function requestedWhatsAppContact() {
  try {
    return new URL(window.location.href).searchParams.get("contact") === "whatsapp";
  } catch {
    return false;
  }
}

function installMobileNavigation() {
  const button = document.querySelector("#menuToggle");
  const bar = document.querySelector(".topbar");
  const nav = document.querySelector("#siteNavigation");
  if (!button || !bar || !nav) return;
  button.hidden = false;
  bar.dataset.enhanced = "";
  function close() {
    bar.removeAttribute("data-menu-open");
    button.setAttribute("aria-expanded", "false");
  }
  button.addEventListener("click", () => {
    const open = button.getAttribute("aria-expanded") !== "true";
    button.setAttribute("aria-expanded", String(open));
    bar.toggleAttribute("data-menu-open", open);
  });
  nav.addEventListener("click", (event) => { if (event.target.closest("a")) close(); });
  bar.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && button.getAttribute("aria-expanded") === "true") { close(); button.focus(); }
  });
}

async function init() {
  installMobileNavigation();
  enhanceSkillIcons();
  const languageController = createLanguageController({
    pdfs: PDFS,
    onApplied(state) {
      updateMainDocumentTitle(state);
    },
    initialLanguage: document.documentElement.lang
  });
  await languageController.tryApply(languageController.language);

  const stats = createStatsController(languageController);
  bindStatsVisibility(stats);

  const activateContact = installLazyContact(languageController);
  if (requestedWhatsAppContact()) await activateContact?.();

  createNavigationObserver();
}

if (typeof document !== "undefined") {
  installPreloadErrorRecovery(window);
  window.addEventListener("DOMContentLoaded", init, { once: true });
}
