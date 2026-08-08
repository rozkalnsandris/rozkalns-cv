function setStatus(root, message, state = "") {
  const status = root.querySelector("#contactVerifyStatus");
  if (!status) return;
  status.textContent = message;
  status.dataset.state = state;
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
    script.addEventListener(
      "load",
      () => windowLike.turnstile ? resolve(windowLike.turnstile) : reject(new Error("turnstile unavailable")),
      { once: true }
    );
    script.addEventListener("error", () => reject(new Error("turnstile unavailable")), { once: true });
    root.head.append(script);
  });
  return turnstilePromise;
}

function revealLink(root, element, value, href) {
  const link = root.createElement("a");
  link.href = href;
  link.textContent = value;
  element.replaceWith(link);
  link.dataset.revealed = "true";
  return link;
}

export function contactPayloadIsValid(payload) {
  return Boolean(
    payload &&
    typeof payload === "object" &&
    typeof payload.email === "string" &&
    payload.email.includes("@") &&
    typeof payload.phone === "string" &&
    typeof payload.phone_uri === "string" &&
    /^\+[0-9]{8,15}$/.test(payload.phone_uri)
  );
}

export function createContactController(languageController, {
  root = globalThis.document,
  windowLike = globalThis.window,
  fetchImpl = globalThis.fetch
} = {}) {
  const button = root.querySelector("#contactReveal");
  const mount = root.querySelector("#turnstileMount");
  if (!button || !mount) return null;

  const message = (key) => {
    const value = languageController.messages?.[key];
    return typeof value === "string" ? value : "";
  };

  function refreshCopy() {
    const label = button.querySelector(".contact-reveal-label");
    const email = root.querySelector("#contactEmail");
    const phone = root.querySelector("#contactPhone");
    if (label && !button.dataset.locked) {
      label.textContent = message("contact_reveal");
    }
    if (email && email.dataset.revealed !== "true") {
      email.setAttribute("aria-label", message("contact_email_hidden"));
    }
    if (phone && phone.dataset.revealed !== "true") {
      phone.setAttribute("aria-label", message("contact_phone_hidden"));
    }
  }

  async function submitToken(token, turnstile, widgetId) {
    setStatus(root, message("contact_verifying"));
    const response = await fetchImpl("/api/contact-reveal", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
      body: JSON.stringify({ token })
    });
    let payload = null;
    try { payload = await response.json(); } catch {}
    if (!response.ok || !contactPayloadIsValid(payload)) {
      setStatus(root, message("contact_failed"), "error");
      turnstile.reset(widgetId);
      return false;
    }
    const email = root.querySelector("#contactEmail");
    const phone = root.querySelector("#contactPhone");
    const emailLink = email ? revealLink(root, email, payload.email, `mailto:${payload.email}`) : null;
    const phoneLink = phone ? revealLink(root, phone, payload.phone, `tel:${payload.phone_uri}`) : null;
    button.hidden = true;
    mount.hidden = true;
    setStatus(root, message("contact_success"), "success");
    windowLike.setTimeout(() => (emailLink || phoneLink)?.focus(), 0);
    return true;
  }

  async function start() {
    button.disabled = true;
    button.dataset.locked = "true";
    setStatus(root, message("contact_loading"));
    try {
      const configResponse = await fetchImpl("/api/contact-config", { cache: "no-store" });
      const config = await configResponse.json();
      if (!configResponse.ok || !config?.configured || typeof config.sitekey !== "string" || !config.sitekey) {
        throw new Error("contact verification is not configured");
      }
      const turnstile = await loadTurnstile(root, windowLike);
      mount.hidden = false;
      let widgetId = null;
      widgetId = turnstile.render(mount, {
        sitekey: config.sitekey,
        theme: "dark",
        size: "flexible",
        appearance: "interaction-only",
        action: "contact_reveal",
        callback: (token) => submitToken(token, turnstile, widgetId),
        "error-callback": () => setStatus(root, message("contact_failed"), "error"),
        "expired-callback": () => turnstile.reset(widgetId)
      });
    } catch {
      setStatus(root, message("contact_unavailable"), "error");
      button.disabled = false;
      delete button.dataset.locked;
      refreshCopy();
    }
  }

  refreshCopy();
  button.addEventListener("click", start);
  const observer = new MutationObserver(refreshCopy);
  observer.observe(root.documentElement, { attributes: true, attributeFilter: ["lang"] });
  return { start, refreshCopy };
}
