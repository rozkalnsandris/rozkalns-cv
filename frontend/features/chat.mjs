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
  message.setAttribute("role", "listitem");
  log.append(message);
  log.scrollTop = log.scrollHeight;
  return message;
}

let turnstilePromise = null;
function loadTurnstile(root, windowLike) {
  if (windowLike.turnstile) return Promise.resolve(windowLike.turnstile);
  if (turnstilePromise) return turnstilePromise;
  turnstilePromise = new Promise((resolve, reject) => {
    const script = root.createElement("script");
    script.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
    script.async = true;
    script.defer = true;
    script.addEventListener("load", () => {
      if (windowLike.turnstile) resolve(windowLike.turnstile);
      else reject(new Error("chat verification unavailable"));
    }, { once: true });
    script.addEventListener("error", () => reject(new Error("chat verification unavailable")), { once: true });
    root.head.append(script);
  });
  return turnstilePromise;
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
  if (!form || !input || !send || !log || !status) return null;
  const completedHistory = [];
  let admissionSession = "";
  let admissionPromise = null;

  async function ensureAdmission() {
    if (admissionSession) return admissionSession;
    if (admissionPromise) return admissionPromise;
    admissionPromise = (async () => {
      const configResponse = await fetchImpl("/api/chat-config", { cache: "no-store" });
      const config = await configResponse.json();
      if (!configResponse.ok || !config?.configured || typeof config.sitekey !== "string" || !config.sitekey) {
        throw new Error("Chat verification is temporarily unavailable. Please email Andris instead.");
      }
      const turnstile = await loadTurnstile(root, windowLike);
      const mount = root.createElement("div");
      mount.className = "turnstile-mount";
      status.after(mount);
      return new Promise((resolve, reject) => {
        let widgetId = null;
        const cleanup = () => mount.remove();
        widgetId = turnstile.render(mount, {
          sitekey: config.sitekey,
          theme: "dark",
          size: "flexible",
          appearance: "interaction-only",
          action: "chat_admission",
          callback: async (token) => {
            try {
              const response = await fetchImpl("/api/chat-admission", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                cache: "no-store",
                body: JSON.stringify({ token })
              });
              const payload = await response.json();
              if (!response.ok || typeof payload?.session !== "string" || !payload.session) {
                turnstile.reset(widgetId);
                throw new Error(payload?.reply || "Chat verification failed. Please try again.");
              }
              admissionSession = payload.session;
              cleanup();
              resolve(admissionSession);
            } catch (error) {
              cleanup();
              reject(error);
            }
          },
          "error-callback": () => {
            cleanup();
            reject(new Error("Chat verification failed. Please try again."));
          },
          "expired-callback": () => turnstile.reset(widgetId)
        });
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
    status.textContent = languageController.messages?.chat_typing || "Preparing answer…";

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
        let errorMessage = languageController.messages?.chat_error || "Connection issue.";
        try {
          const body = await response.json();
          if (typeof body.reply === "string") errorMessage = body.reply;
        } catch {}
        throw new Error(errorMessage);
      }
      if (!response.body) throw new Error("stream unavailable");
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
      completedHistory.push(
        { role: "user", content: message },
        { role: "assistant", content: full }
      );
      status.textContent = languageController.messages?.chat_complete || "Answer complete.";
    } catch (error) {
      const text = error instanceof Error && error.message
        ? error.message
        : (languageController.messages?.chat_error || "Connection issue.");
      appendMessage(root, log, text, "bot");
      status.textContent = text;
    } finally {
      send.disabled = false;
      form.setAttribute("aria-busy", "false");
      input.focus();
    }
  });
  return { completedHistory };
}
