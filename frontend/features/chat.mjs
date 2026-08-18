import providerNotices from "../../bot/provider_notices.json" with { type: "json" };
import { createLocalizedTurnstileRenderer, loadTurnstile } from "../core/turnstile.mjs";

const CHAT_STATUS = Object.freeze({
  typing: Object.freeze({ key: "chat_typing", fallback: "Preparing answer…" }),
  complete: Object.freeze({ key: "chat_complete", fallback: "Answer complete." }),
  error: Object.freeze({ key: "chat_error", fallback: "Connection issue." })
});

const PRIVACY_FALLBACK = "Messages are processed by the configured LLM provider. Chat retention details are currently unavailable; raw IP addresses are not stored.";
const PRIVACY_ZERO_FALLBACK = "Messages are processed by the configured LLM provider. Raw chat content is not retained; raw IP addresses are not stored.";
const PRIVACY_RETAINED_FALLBACK = "Messages are processed by the configured LLM provider. Raw chat content may be retained for up to {days} days under a pseudonymous identifier; raw IP addresses are not stored.";
const PROVIDER_FAILURE_NOTICES = Object.freeze(Object.values(providerNotices));

export function normalizeChatRetentionDays(value) {
  return Number.isInteger(value) && value >= 0 ? value : null;
}

export function renderChatPrivacyText(messages, retentionDays) {
  const normalized = normalizeChatRetentionDays(retentionDays);
  if (normalized === 0) {
    const value = messages?.chat_privacy_zero;
    return typeof value === "string" && value ? value : PRIVACY_ZERO_FALLBACK;
  }
  if (normalized !== null) {
    const template = messages?.chat_privacy_retained;
    const value = typeof template === "string" && template ? template : PRIVACY_RETAINED_FALLBACK;
    return value.replaceAll("{days}", String(normalized));
  }
  const value = messages?.chat_privacy;
  return typeof value === "string" && value ? value : PRIVACY_FALLBACK;
}

export function chatStreamSucceeded(text) {
  const full = String(text ?? "");
  return Boolean(full.trim()) && !PROVIDER_FAILURE_NOTICES.some((notice) => full.endsWith(notice));
}

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
  return { message: current, history: normalizeCompletedHistory(history) };
}

function focusableElements(container) {
  return [...container.querySelectorAll(
    'a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])'
  )].filter((element) => !element.hidden);
}

export function createDialogController({ root = globalThis.document, windowLike = globalThis.window } = {}) {
  const launcher = root.querySelector("#chatLauncher");
  const backdrop = root.querySelector("#chatBackdrop");
  const dialog = root.querySelector("#chatDialog");
  const shell = root.querySelector("#pageShell");
  const input = root.querySelector("#chatInput");
  const close = root.querySelector("#chatClose");
  if (!launcher || !backdrop || !dialog || !shell || !input || !close) return null;
  let returnFocus = launcher;

  function open() {
    returnFocus = root.activeElement instanceof HTMLElement ? root.activeElement : launcher;
    backdrop.hidden = false;
    shell.inert = true;
    root.body.classList.add("dialog-open");
    launcher.hidden = true;
    windowLike.setTimeout(() => input.focus(), 0);
  }

  function dismiss() {
    backdrop.hidden = true;
    shell.inert = false;
    root.body.classList.remove("dialog-open");
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
    if (event.shiftKey && root.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && root.activeElement === last) {
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

function appendMessage(root, log, text, role) {
  const message = root.createElement("div");
  message.className = `message ${role}`;
  message.textContent = text;
  log.append(message);
  log.scrollTop = log.scrollHeight;
  return message;
}

export function createChatController(languageController, {
  root = globalThis.document,
  windowLike = globalThis.window,
  fetchImpl = globalThis.fetch
} = {}) {
  const form = root.querySelector("#chatForm");
  const input = root.querySelector("#chatInput");
  const send = root.querySelector("#chatSend");
  const log = root.querySelector("#chatLog");
  const status = root.querySelector("#chatStatus");
  const privacy = root.querySelector("#chatPrivacy");
  if (!form || !input || !send || !log || !status) return null;
  const completedHistory = [];
  let admissionSession = "";
  let admissionPromise = null;
  let admissionWidget = null;
  let admissionVerificationPending = false;
  let currentStatus = null;
  let retentionDays = null;

  function localized(key, fallback) {
    const value = languageController.messages?.[key];
    return typeof value === "string" && value ? value : fallback;
  }

  function renderStatus() {
    if (!currentStatus) return false;
    const definition = CHAT_STATUS[currentStatus];
    if (!definition) return false;
    status.textContent = localized(definition.key, definition.fallback);
    return true;
  }

  function renderPrivacy() {
    if (!privacy) return false;
    privacy.textContent = renderChatPrivacyText(languageController.messages, retentionDays);
    return true;
  }

  async function loadPrivacyPolicy() {
    renderPrivacy();
    try {
      const response = await fetchImpl("/api/chat-config", { cache: "no-store" });
      const config = await response.json();
      retentionDays = response.ok ? normalizeChatRetentionDays(config?.retention_days) : null;
    } catch {
      retentionDays = null;
    }
    renderPrivacy();
    return retentionDays;
  }

  function setStatus(nextStatus) {
    currentStatus = nextStatus;
    return renderStatus();
  }

  function genericErrorText() {
    const definition = CHAT_STATUS.error;
    return localized(definition.key, definition.fallback);
  }

  function refreshLanguageSensitiveState() {
    renderStatus();
    renderPrivacy();
    if (!admissionVerificationPending) admissionWidget?.refreshLanguage();
  }

  const Observer = windowLike?.MutationObserver || globalThis.MutationObserver;
  if (typeof Observer === "function" && root.documentElement) {
    new Observer(refreshLanguageSensitiveState).observe(root.documentElement, {
      attributes: true,
      attributeFilter: ["lang"]
    });
  }

  const privacyReady = privacy ? loadPrivacyPolicy() : Promise.resolve(null);

  async function ensureAdmission() {
    if (admissionSession) return admissionSession;
    if (admissionPromise) return admissionPromise;
    admissionPromise = (async () => {
      const configResponse = await fetchImpl("/api/chat-config", { cache: "no-store" });
      const config = await configResponse.json();
      if (!configResponse.ok || !config?.configured || typeof config.sitekey !== "string" || !config.sitekey) {
        throw new Error(genericErrorText());
      }
      let turnstile = null;
      try {
        turnstile = await loadTurnstile(root, windowLike);
      } catch {
        throw new Error(genericErrorText());
      }
      const mount = root.createElement("div");
      mount.className = "turnstile-mount";
      status.after(mount);
      return new Promise((resolve, reject) => {
        const cleanup = () => {
          admissionWidget = null;
          mount.remove();
        };
        admissionWidget = createLocalizedTurnstileRenderer(
          turnstile,
          mount,
          () => ({
            sitekey: config.sitekey,
            theme: "dark",
            size: "flexible",
            appearance: "interaction-only",
            action: "chat_admission",
            callback: async (token) => {
              admissionVerificationPending = true;
              try {
                const response = await fetchImpl("/api/chat-admission", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  cache: "no-store",
                  body: JSON.stringify({ token })
                });
                const payload = await response.json();
                if (!response.ok || typeof payload?.session !== "string" || !payload.session) {
                  turnstile.reset(admissionWidget.widgetId);
                  throw new Error(payload?.reply || genericErrorText());
                }
                admissionSession = payload.session;
                cleanup();
                resolve(admissionSession);
              } catch (error) {
                cleanup();
                reject(error);
              } finally {
                admissionVerificationPending = false;
              }
            },
            "error-callback": () => {
              cleanup();
              reject(new Error(genericErrorText()));
            },
            "expired-callback": () => turnstile.reset(admissionWidget.widgetId)
          }),
          { root }
        );
        admissionWidget.render();
      });
    })().finally(() => { admissionPromise = null; });
    return admissionPromise;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = input.value.trim();
    if (!message) return;
    input.value = "";
    send.disabled = true;
    form.setAttribute("aria-busy", "true");
    appendMessage(root, log, message, "user");
    setStatus("typing");

    try {
      const session = await ensureAdmission();
      const response = await fetchImpl("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Chat-Admission": session
        },
        body: JSON.stringify(buildChatPayload(message, completedHistory))
      });
      if (!response.ok) {
        if (response.status === 401) admissionSession = "";
        let errorMessage = genericErrorText();
        try {
          const body = await response.json();
          if (typeof body.reply === "string") errorMessage = body.reply;
        } catch {}
        throw new Error(errorMessage);
      }
      if (!response.body) throw new Error(genericErrorText());
      const answer = appendMessage(root, log, "", "bot");
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
      if (chatStreamSucceeded(full)) {
        completedHistory.push(
          { role: "user", content: message },
          { role: "assistant", content: full }
        );
        setStatus("complete");
      } else {
        setStatus("error");
      }
    } catch (error) {
      const text = error instanceof Error && error.message
        ? error.message
        : genericErrorText();
      appendMessage(root, log, text, "bot");
      setStatus("error");
    } finally {
      send.disabled = false;
      form.setAttribute("aria-busy", "false");
      input.focus();
    }
  });
  return { completedHistory, rerender: refreshLanguageSensitiveState, privacyReady };
}