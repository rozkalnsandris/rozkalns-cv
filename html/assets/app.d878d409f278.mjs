const TRANSLATIONS = Object.freeze({
  en: "/i18n/en.f5b04cdd45df.json",
  de: "/i18n/de.3313b3cef4b0.json",
  lv: "/i18n/lv.788ab6598ca4.json"
});

const PDFS = Object.freeze({
  en: "/cv.pdf",
  de: "/cv-de.pdf",
  lv: "/cv-lv.pdf"
});

export const REQUIRED_STATS = Object.freeze([
  "updated", "uptime_30d", "docker_containers", "load1", "days_online",
  "cpu_usage", "ram_usage", "disk_usage", "cpu_temp"
]);

export function normalizeCompletedHistory(history, maxMessages = 12) {
  if (!Array.isArray(history)) return [];
  const completed = [];
  for (let index = 0; index + 1 < history.length; index += 2) {
    const user = history[index];
    const assistant = history[index + 1];
    if (
      user?.role !== "user" ||
      assistant?.role !== "assistant" ||
      typeof user.content !== "string" ||
      typeof assistant.content !== "string" ||
      !user.content.trim() ||
      !assistant.content.trim()
    ) {
      break;
    }
    completed.push(
      { role: "user", content: user.content.trim() },
      { role: "assistant", content: assistant.content.trim() }
    );
  }
  return completed.slice(-maxMessages);
}

export function buildChatPayload(message, history) {
  const current = String(message ?? "").trim();
  if (!current) throw new TypeError("message is required");
  return {
    message: current,
    history: normalizeCompletedHistory(history)
  };
}

export function validateStats(payload, nowMs = Date.now()) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return { valid: false, state: "offline", reason: "shape" };
  }
  for (const key of REQUIRED_STATS) {
    if (!(key in payload)) return { valid: false, state: "offline", reason: `missing:${key}` };
  }
  const timestamp = Date.parse(payload.updated);
  if (!Number.isFinite(timestamp)) {
    return { valid: false, state: "offline", reason: "timestamp" };
  }
  const ageMinutes = (nowMs - timestamp) / 60000;
  if (!Number.isFinite(ageMinutes) || ageMinutes < -5) {
    return { valid: false, state: "offline", reason: "future" };
  }
  for (const [key, value] of Object.entries(payload)) {
    if (key === "updated") continue;
    if (value !== null && (typeof value !== "number" || !Number.isFinite(value))) {
      return { valid: false, state: "offline", reason: `number:${key}` };
    }
  }
  return {
    valid: true,
    state: ageMinutes > 15 ? "stale" : "live",
    ageMinutes,
    timestamp
  };
}

function preferredLanguage() {
  try {
    const saved = localStorage.getItem("cvlang");
    if (saved && TRANSLATIONS[saved]) return saved;
  } catch {}
  const candidate = (navigator.language || "en").slice(0, 2).toLowerCase();
  return TRANSLATIONS[candidate] ? candidate : "en";
}

async function loadTranslation(language) {
  const response = await fetch(TRANSLATIONS[language], { cache: "force-cache" });
  if (!response.ok) throw new Error("translation unavailable");
  const data = await response.json();
  if (!data || typeof data !== "object") throw new Error("translation invalid");
  return data;
}

function translateDocument(data, language) {
  document.documentElement.lang = language;
  document.querySelectorAll("[data-i18n]").forEach((element) => {
    const value = data[element.dataset.i18n];
    if (typeof value === "string") element.textContent = value;
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
    const value = data[element.dataset.i18nPlaceholder];
    if (typeof value === "string") element.setAttribute("placeholder", value);
  });
  document.querySelectorAll("[data-i18n-label]").forEach((element) => {
    const value = data[element.dataset.i18nLabel];
    if (typeof value === "string") element.setAttribute("aria-label", value);
  });
  document.querySelectorAll("[data-lang]").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.lang === language));
  });
  const pdf = document.querySelector("#pdfLink");
  if (pdf) pdf.setAttribute("href", PDFS[language]);
  try { localStorage.setItem("cvlang", language); } catch {}
}

function createLanguageController() {
  let language = preferredLanguage();
  let messages = null;
  async function apply(nextLanguage) {
    const safeLanguage = TRANSLATIONS[nextLanguage] ? nextLanguage : "en";
    messages = await loadTranslation(safeLanguage);
    language = safeLanguage;
    translateDocument(messages, language);
    return messages;
  }
  return {
    apply,
    get language() { return language; },
    get messages() { return messages; }
  };
}

function setStatus(state, messages) {
  const dot = document.querySelector("#liveDot");
  const label = document.querySelector("#liveLabel");
  if (!dot || !label) return;
  dot.dataset.state = state;
  const key = state === "live" ? "status_live" : state === "stale" ? "status_stale" : "status_offline";
  label.textContent = messages?.[key] || state;
}

function renderStats(payload, validation, language, messages) {
  document.querySelectorAll("[data-stat]").forEach((element) => {
    const value = payload[element.dataset.stat];
    if (value === null || value === undefined) {
      element.textContent = "—";
      return;
    }
    const decimals = Number.parseInt(element.dataset.decimals || "0", 10);
    const suffix = element.dataset.suffix || "";
    element.textContent = `${Number(value).toFixed(decimals)}${suffix}`;
  });
  const date = new Date(validation.timestamp);
  const stamp = date.toLocaleString(language === "de" ? "de-DE" : language === "lv" ? "lv-LV" : "en-GB", {
    day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit"
  });
  const updated = document.querySelector("#statsUpdated");
  if (updated) updated.textContent = `${messages?.last_update || "Last update"}: ${stamp}`;
  setStatus(validation.state, messages);
}

function createStatsController(languageController) {
  let timer = null;
  async function load() {
    try {
      const response = await fetch(`/stats.json?_=${Date.now()}`, { cache: "no-store" });
      if (!response.ok) throw new Error("stats unavailable");
      const payload = await response.json();
      const validation = validateStats(payload);
      if (!validation.valid) throw new Error(validation.reason);
      renderStats(payload, validation, languageController.language, languageController.messages);
    } catch {
      setStatus("offline", languageController.messages);
      const updated = document.querySelector("#statsUpdated");
      if (updated) updated.textContent = "—";
    }
  }
  function start() {
    window.clearInterval(timer);
    load();
    timer = window.setInterval(load, 60000);
  }
  function stop() { window.clearInterval(timer); }
  return { load, start, stop };
}

function focusableElements(container) {
  return [...container.querySelectorAll(
    'a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])'
  )].filter((element) => !element.hidden);
}

function createDialogController() {
  const launcher = document.querySelector("#chatLauncher");
  const backdrop = document.querySelector("#chatBackdrop");
  const dialog = document.querySelector("#chatDialog");
  const shell = document.querySelector("#pageShell");
  const input = document.querySelector("#chatInput");
  const close = document.querySelector("#chatClose");
  if (!launcher || !backdrop || !dialog || !shell || !input || !close) return null;
  let returnFocus = launcher;

  function open() {
    returnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : launcher;
    backdrop.hidden = false;
    shell.inert = true;
    document.body.classList.add("dialog-open");
    launcher.hidden = true;
    window.setTimeout(() => input.focus(), 0);
  }

  function dismiss() {
    backdrop.hidden = true;
    shell.inert = false;
    document.body.classList.remove("dialog-open");
    launcher.hidden = false;
    returnFocus?.focus();
  }

  function onKeydown(event) {
    if (event.key === "Escape") {
      event.preventDefault();
      dismiss();
      return;
    }
    if (event.key !== "Tab") return;
    const items = focusableElements(dialog);
    if (!items.length) return;
    const first = items[0];
    const last = items[items.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  launcher.addEventListener("click", open);
  close.addEventListener("click", dismiss);
  backdrop.addEventListener("click", (event) => { if (event.target === backdrop) dismiss(); });
  dialog.addEventListener("keydown", onKeydown);
  return { open, dismiss };
}

function appendMessage(log, text, role) {
  const message = document.createElement("div");
  message.className = `message ${role}`;
  message.textContent = text;
  message.setAttribute("role", "listitem");
  log.append(message);
  log.scrollTop = log.scrollHeight;
  return message;
}

function createChatController(languageController) {
  const form = document.querySelector("#chatForm");
  const input = document.querySelector("#chatInput");
  const send = document.querySelector("#chatSend");
  const log = document.querySelector("#chatLog");
  const status = document.querySelector("#chatStatus");
  if (!form || !input || !send || !log || !status) return null;
  const completedHistory = [];

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = input.value.trim();
    if (!message) return;
    input.value = "";
    send.disabled = true;
    form.setAttribute("aria-busy", "true");
    appendMessage(log, message, "user");
    status.textContent = languageController.messages?.chat_typing || "Preparing answer…";

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildChatPayload(message, completedHistory))
      });
      if (!response.ok) {
        let errorMessage = languageController.messages?.chat_error || "Connection issue.";
        try {
          const body = await response.json();
          if (typeof body.reply === "string") errorMessage = body.reply;
        } catch {}
        throw new Error(errorMessage);
      }
      if (!response.body) throw new Error("stream unavailable");
      const answer = appendMessage(log, "", "bot");
      answer.setAttribute("aria-live", "off");
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let full = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        full += decoder.decode(value, { stream: true });
        answer.textContent = full;
        log.scrollTop = log.scrollHeight;
      }
      full += decoder.decode();
      answer.textContent = full;
      completedHistory.push(
        { role: "user", content: message },
        { role: "assistant", content: full }
      );
      status.textContent = languageController.messages?.chat_complete || "Answer complete.";
    } catch (error) {
      const text = error instanceof Error && error.message ? error.message : (languageController.messages?.chat_error || "Connection issue.");
      appendMessage(log, text, "bot");
      status.textContent = text;
    } finally {
      send.disabled = false;
      form.setAttribute("aria-busy", "false");
      input.focus();
    }
  });
  return { completedHistory };
}

function createNavigationObserver() {
  if (!("IntersectionObserver" in window)) return;
  const links = [...document.querySelectorAll(".site-nav a")];
  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      for (const link of links) {
        link.removeAttribute("aria-current");
        if (link.getAttribute("href") === `#${entry.target.id}`) link.setAttribute("aria-current", "true");
      }
    }
  }, { rootMargin: "-30% 0px -60% 0px" });
  document.querySelectorAll("main section[id]").forEach((section) => observer.observe(section));
}

async function init() {
  const languageController = createLanguageController();
  try { await languageController.apply(languageController.language); }
  catch { await languageController.apply("en"); }

  document.querySelectorAll("[data-lang]").forEach((button) => {
    button.addEventListener("click", async () => {
      await languageController.apply(button.dataset.lang);
    });
  });

  const stats = createStatsController(languageController);
  stats.start();
  document.addEventListener("visibilitychange", () => document.hidden ? stats.stop() : stats.start());
  createDialogController();
  createChatController(languageController);
  createNavigationObserver();
}

if (typeof document !== "undefined") {
  window.addEventListener("DOMContentLoaded", init, { once: true });
}
