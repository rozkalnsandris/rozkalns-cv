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

const PRIMARY_PROJECT_PROOF = Object.freeze([
  "https://github.com/rozkalnsandris/hermes-tech",
  "https://github.com/rozkalnsandris/RPi5_main",
  "https://github.com/rozkalnsandris/home-assistant-config"
]);

export { REQUIRED_STATS, validateStats };

export function updateMainDocumentTitle({ messages }, { documentLike = globalThis.document } = {}) {
  const role = messages?.role;
  if (!documentLike || typeof role !== "string" || !role.startsWith("Junior ")) return false;
  const titleRole = role.slice("Junior ".length).trim();
  if (!titleRole) return false;
  documentLike.title = `Andris Rožkalns · ${titleRole}`;
  return true;
}

export function updateChatLauncherLabel({ messages }, {
  documentLike = globalThis.document,
  viewportWidth = globalThis.innerWidth
} = {}) {
  const launcher = documentLike?.querySelector?.("#chatLauncher");
  const width = Number(viewportWidth);
  if (!launcher || !Number.isFinite(width)) return false;
  const key = width >= 720 && width < 1560 ? "chat_title" : "chat_open";
  const label = messages?.[key];
  if (typeof label !== "string" || !label.trim()) return false;
  launcher.textContent = label;
  return true;
}

export function updateChatLauncherPlacement({
  documentLike = globalThis.document,
  viewportWidth = globalThis.innerWidth,
  rightInset = 14
} = {}) {
  const launcher = documentLike?.querySelector?.("#chatLauncher");
  const page = documentLike?.querySelector?.("#pageShell");
  const actions = documentLike?.querySelector?.(".actions");
  const body = documentLike?.body;
  const width = Number(documentLike?.documentElement?.clientWidth) || Number(viewportWidth);
  const pageRect = page?.getBoundingClientRect?.();
  const launcherRect = launcher?.getBoundingClientRect?.();
  if (!launcher || !actions || !body || !pageRect || !launcherRect || !Number.isFinite(width)) return false;
  const launcherWidth = Math.max(launcherRect.width, Number(launcher.scrollWidth) || 0);
  const rail = width - pageRect.right >= launcherWidth + rightInset;
  launcher.classList.toggle("chat-launcher-inline", !rail);
  launcher.dataset.placement = rail ? "rail" : "inline";
  if (rail && launcher.parentElement !== body) {
    body.insertBefore(launcher, documentLike.querySelector?.("#chatBackdrop") || null);
  } else if (!rail && launcher.parentElement !== actions) {
    actions.append(launcher);
  }
  return true;
}

export function installRecruiterProofLinks({ documentLike = globalThis.document } = {}) {
  if (typeof documentLike?.querySelector !== "function" || typeof documentLike?.createElement !== "function") {
    return false;
  }

  const actions = documentLike.querySelector(".actions");
  const projects = [...(documentLike.querySelectorAll?.(".project-entry.primary") || [])];
  if (!actions || projects.length < PRIMARY_PROJECT_PROOF.length) return false;

  let changed = false;

  for (const [index, href] of PRIMARY_PROJECT_PROOF.entries()) {
    const project = projects[index];
    let proofLinks = project.querySelector?.(".project-proof-links");
    if (!proofLinks) {
      proofLinks = documentLike.createElement("div");
      proofLinks.className = "project-proof-links";
      project.querySelector?.(".project-copy")?.append(proofLinks);
      changed = true;
    }

    if (proofLinks && !proofLinks.querySelector?.(`a[href="${href}"]`)) {
      const link = documentLike.createElement("a");
      const title = project.querySelector?.("h3")?.textContent?.trim() || "Project";
      link.className = "project-proof-link";
      link.href = href;
      link.rel = "me";
      link.setAttribute("aria-label", `${title} on GitHub`);
      link.textContent = "GitHub ↗";
      proofLinks.append(link);
      changed = true;
    }
  }

  const smartDemo = actions.querySelector?.('a[href="/smarthome.html"]');
  const homeProofLinks = projects[2]?.querySelector?.(".project-proof-links");
  if (smartDemo && homeProofLinks && smartDemo.parentElement !== homeProofLinks) {
    smartDemo.classList.remove("button");
    smartDemo.classList.add("project-proof-link", "project-demo-link");
    homeProofLinks.append(smartDemo);
    changed = true;
  }

  if (!documentLike.querySelector("#githubCta")) {
    const githubCta = documentLike.createElement("a");
    githubCta.id = "githubCta";
    githubCta.className = "button recruiter-github-cta";
    githubCta.href = "https://github.com/rozkalnsandris";
    githubCta.rel = "me";
    githubCta.textContent = "GitHub";
    actions.append(githubCta);
    changed = true;
  }

  return changed;
}

function syncChatLauncher(messages) {
  updateChatLauncherLabel({ messages });
  updateChatLauncherPlacement();
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
  installRecruiterProofLinks();
  enhanceSkillIcons();
  const languageController = createLanguageController({
    pdfs: PDFS,
    onApplied(state) {
      updateMainDocumentTitle(state);
      syncChatLauncher(state.messages);
    },
    initialLanguage: document.documentElement.lang
  });
  await languageController.tryApply(languageController.language);

  const stats = createStatsController(languageController);
  bindStatsVisibility(stats);

  const activateContact = installLazyContact(languageController);
  if (requestedWhatsAppContact()) await activateContact?.();

  installLazyChat(languageController);
  window.addEventListener("resize", () => syncChatLauncher(languageController.messages), { passive: true });
  createNavigationObserver();
}

if (typeof document !== "undefined") {
  installPreloadErrorRecovery(window);
  window.addEventListener("DOMContentLoaded", init, { once: true });
}
