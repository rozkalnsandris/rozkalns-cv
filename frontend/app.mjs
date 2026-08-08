import { createLanguageController } from "./core/i18n.mjs";
import {
  bindStatsVisibility,
  createStatsController,
  REQUIRED_STATS,
  validateStats
} from "./features/stats.mjs";
import { PUBLIC_EMAIL, WHATSAPP_CONTACT_URL } from "./public-contact.mjs";
import { enhanceSkillIcons } from "./ui/icons.mjs";

const PDFS = Object.freeze({
  en: "/cv.pdf",
  de: "/cv-de.pdf",
  lv: "/cv-lv.pdf"
});
const WHATSAPP_QR_URL = new URL("./media/whatsapp-contact-qr.svg", import.meta.url).href;

export { REQUIRED_STATS, validateStats };

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

function installPublicContactPresentation() {
  const email = document.querySelector("#contactEmail");
  if (email) {
    const link = document.createElement("a");
    link.id = "contactEmail";
    link.href = `mailto:${PUBLIC_EMAIL}`;
    link.textContent = PUBLIC_EMAIL;
    link.dataset.publicContact = "email";
    email.replaceWith(link);
  }

  const phone = document.querySelector("#contactPhone");
  phone?.closest(".contact-row")?.classList.add("protected-phone-row");

  const contacts = document.querySelector(".contacts");
  if (!contacts || document.querySelector(".print-whatsapp-contact")) return;

  const card = document.createElement("a");
  card.className = "print-whatsapp-contact";
  card.href = WHATSAPP_CONTACT_URL;
  card.setAttribute("aria-label", "Verified WhatsApp contact");

  const image = document.createElement("img");
  image.src = WHATSAPP_QR_URL;
  image.alt = "WhatsApp contact QR code";
  image.width = 96;
  image.height = 96;

  const copy = document.createElement("span");
  copy.className = "print-whatsapp-copy";
  const label = document.createElement("strong");
  label.dataset.i18n = "whatsapp_qr_label";
  label.textContent = "WhatsApp / phone";
  const hint = document.createElement("small");
  hint.dataset.i18n = "whatsapp_qr_hint";
  hint.textContent = "Scan to verify and open WhatsApp";
  copy.append(label, hint);
  card.append(image, copy);
  contacts.after(card);
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

function requestedLanguage() {
  try {
    const value = new URL(window.location.href).searchParams.get("lang");
    return value && ["en", "de", "lv"].includes(value) ? value : null;
  } catch {
    return null;
  }
}

function requestedWhatsAppContact() {
  try {
    return new URL(window.location.href).searchParams.get("contact") === "whatsapp";
  } catch {
    return false;
  }
}

async function init() {
  installPublicContactPresentation();
  const languageController = createLanguageController({ pdfs: PDFS });
  try { await languageController.apply(requestedLanguage() || languageController.language); }
  catch { await languageController.apply("en"); }

  document.querySelectorAll("[data-lang]").forEach((button) => {
    button.addEventListener("click", async () => {
      await languageController.apply(button.dataset.lang);
    });
  });

  enhanceSkillIcons();
  const activateContact = installLazyContact(languageController);
  if (requestedWhatsAppContact()) await activateContact?.();

  const stats = createStatsController(languageController);
  bindStatsVisibility(stats);

  installLazyChat(languageController);
  createNavigationObserver();
}

if (typeof document !== "undefined") {
  window.addEventListener("DOMContentLoaded", init, { once: true });
}
