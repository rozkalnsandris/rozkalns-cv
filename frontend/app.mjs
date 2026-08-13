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

function installLazyChat(languageController) {
  const launcher = document.querySelector("#chatLauncher");
  if (!launcher) return;
  let loading = null;

  async function activate() {
    if (loading) return loading;
    loading = import("./features/chat.mjs")
      .then(({ createChatController, createDialogController }) => {
        const dialog = createDialogController();
        const chat = createChatController(languageController);
        if (!dialog || !chat) throw new Error("chat controls unavailable");
        launcher.removeEventListener("click", activate);
        dialog.open();
        return { dialog, chat };
      })
      .catch(() => {
        loading = null;
        return null;
      });
    return loading;
  }

  launcher.addEventListener("click", activate);
}

function installLazyContact(languageController) {
  const button = document.querySelector("#contactReveal");
  if (!button) return null;
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

async function init() {
  const languageController = createLanguageController({ pdfs: PDFS });
  const preferredApplied = await languageController.tryApply(languageController.language);
  if (!preferredApplied) await languageController.tryApply("en");

  const stats = createStatsController(languageController);
  bindStatsVisibility(stats);

  document.querySelectorAll("[data-lang]").forEach((button) => {
    button.addEventListener("click", () => {
      void languageController.tryApply(button.dataset.lang).then((applied) => {
        if (applied) stats.rerender();
      });
    });
  });

  enhanceSkillIcons();
  const activateContact = installLazyContact(languageController);
  if (requestedWhatsAppContact()) await activateContact?.();

  installLazyChat(languageController);
  createNavigationObserver();
}

if (typeof document !== "undefined") {
  installPreloadErrorRecovery(window);
  window.addEventListener("DOMContentLoaded", init, { once: true });
}
