const TEXT = Object.freeze({
  en: {
    reveal: "Verify to show contact details",
    loading: "Loading verification…",
    verifying: "Verifying…",
    success: "Contact details unlocked.",
    failed: "Verification failed. Please try again.",
    unavailable: "Contact verification is temporarily unavailable.",
    emailHidden: "Email address hidden until verification",
    phoneHidden: "Phone number hidden until verification"
  },
  de: {
    reveal: "Prüfen, um Kontaktdaten anzuzeigen",
    loading: "Überprüfung wird geladen…",
    verifying: "Wird überprüft…",
    success: "Kontaktdaten freigeschaltet.",
    failed: "Überprüfung fehlgeschlagen. Bitte erneut versuchen.",
    unavailable: "Kontaktüberprüfung ist vorübergehend nicht verfügbar.",
    emailHidden: "E-Mail-Adresse bis zur Überprüfung verborgen",
    phoneHidden: "Telefonnummer bis zur Überprüfung verborgen"
  },
  lv: {
    reveal: "Pārbaudīt, lai parādītu kontaktus",
    loading: "Ielādē pārbaudi…",
    verifying: "Pārbauda…",
    success: "Kontakti ir atbloķēti.",
    failed: "Pārbaude neizdevās. Mēģini vēlreiz.",
    unavailable: "Kontaktu pārbaude pašlaik nav pieejama.",
    emailHidden: "E-pasts paslēpts līdz pārbaudei",
    phoneHidden: "Tālrunis paslēpts līdz pārbaudei"
  }
});

const ICONS = Object.freeze({
  terminal: ["M4 5h16v14H4z", "m7 9 3 3-3 3", "M12 15h5"],
  container: ["m12 3 8 4-8 4-8-4 8-4Z", "m4 7 8 4 8-4", "M12 11v10", "m4 7v10l8 4 8-4V7"],
  network: ["M5 7h14", "M5 17h14", "M7 5v4", "M17 15v4", "M12 7v10"],
  shield: ["M12 3 19 6v5c0 4.5-2.8 7.7-7 10-4.2-2.3-7-5.5-7-10V6l7-3Z", "m9 12 2 2 4-5"],
  chart: ["M4 19V9", "M10 19V5", "M16 19v-7", "M22 19H2"],
  gear: ["M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z", "M12 2v3M12 19v3M4.9 4.9 7 7M17 17l2.1 2.1M2 12h3M19 12h3M4.9 19.1 7 17M17 7l2.1-2.1"],
  branch: ["M6 3v12a4 4 0 0 0 4 4h4", "M14 5h4v4", "m18 5-4 4", "M6 3h.01"],
  code: ["m8 9-3 3 3 3", "m8-6 3 3-3 3", "m14 5-4 14"],
  home: ["m3 11 9-7 9 7", "M5 10v10h14V10", "M9 20v-6h6v6"],
  chip: ["M8 8h8v8H8z", "M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"],
  cloud: ["M7 18h10a4 4 0 0 0 .8-7.9A6 6 0 0 0 6.4 8.4 4.5 4.5 0 0 0 7 18Z"],
  globe: ["M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z", "M3 12h18", "M12 3c2.5 2.5 3.5 5.5 3.5 9S14.5 18.5 12 21c-2.5-2.5-3.5-5.5-3.5-9S9.5 5.5 12 3Z"]
});

export function skillIconName(label) {
  const value = String(label || "").toLowerCase();
  if (/docker|compose/.test(value)) return "container";
  if (/ssl|tls|ssh|ftp/.test(value)) return "shield";
  if (/prometheus|grafana/.test(value)) return "chart";
  if (/systemd/.test(value)) return "gear";
  if (/git/.test(value)) return "branch";
  if (/python|php|html|css|yaml|bash|linux/.test(value)) return value.includes("bash") || value.includes("linux") ? "terminal" : "code";
  if (/home assistant/.test(value)) return "home";
  if (/esp32|iot/.test(value)) return "chip";
  if (/ansible|terraform|aws|cloud/.test(value)) return "cloud";
  if (/dns|network|rest api|nginx/.test(value)) return "network";
  return "globe";
}

function createIcon(name) {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "1.8");
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
  svg.setAttribute("aria-hidden", "true");
  for (const d of ICONS[name] || ICONS.globe) {
    const path = document.createElementNS(ns, "path");
    path.setAttribute("d", d);
    svg.append(path);
  }
  return svg;
}

export function enhanceSkillIcons(root = document) {
  root.querySelectorAll(".skill-chip").forEach((chip) => {
    if (chip.querySelector("svg")) return;
    chip.prepend(createIcon(skillIconName(chip.textContent)));
  });
}

function language() {
  const value = document.documentElement.lang?.slice(0, 2).toLowerCase();
  return TEXT[value] ? value : "en";
}

function copy() {
  return TEXT[language()];
}

function setStatus(message, state = "") {
  const status = document.querySelector("#contactVerifyStatus");
  if (!status) return;
  status.textContent = message;
  status.dataset.state = state;
}

function refreshContactCopy() {
  const messages = copy();
  const button = document.querySelector("#contactReveal");
  const email = document.querySelector("#contactEmail");
  const phone = document.querySelector("#contactPhone");
  if (button && !button.dataset.locked) button.querySelector(".contact-reveal-label").textContent = messages.reveal;
  if (email && email.dataset.revealed !== "true") email.setAttribute("aria-label", messages.emailHidden);
  if (phone && phone.dataset.revealed !== "true") phone.setAttribute("aria-label", messages.phoneHidden);
}

let turnstilePromise = null;
function loadTurnstile() {
  if (window.turnstile) return Promise.resolve(window.turnstile);
  if (turnstilePromise) return turnstilePromise;
  turnstilePromise = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
    script.async = true;
    script.defer = true;
    script.addEventListener("load", () => window.turnstile ? resolve(window.turnstile) : reject(new Error("turnstile unavailable")), { once: true });
    script.addEventListener("error", () => reject(new Error("turnstile unavailable")), { once: true });
    document.head.append(script);
  });
  return turnstilePromise;
}

function revealLink(element, value, href) {
  const link = document.createElement("a");
  link.href = href;
  link.textContent = value;
  element.replaceWith(link);
  link.dataset.revealed = "true";
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

async function submitToken(token, turnstile, widgetId) {
  const messages = copy();
  setStatus(messages.verifying);
  const response = await fetch("/api/contact-reveal", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    body: JSON.stringify({ token })
  });
  let payload = null;
  try { payload = await response.json(); } catch {}
  if (!response.ok || !contactPayloadIsValid(payload)) {
    setStatus(messages.failed, "error");
    turnstile.reset(widgetId);
    return false;
  }
  const email = document.querySelector("#contactEmail");
  const phone = document.querySelector("#contactPhone");
  if (email) revealLink(email, payload.email, `mailto:${payload.email}`);
  if (phone) revealLink(phone, payload.phone, `tel:${payload.phone_uri}`);
  const button = document.querySelector("#contactReveal");
  const mount = document.querySelector("#turnstileMount");
  if (button) button.hidden = true;
  if (mount) mount.hidden = true;
  setStatus(messages.success, "success");
  return true;
}

async function startContactVerification() {
  const messages = copy();
  const button = document.querySelector("#contactReveal");
  const mount = document.querySelector("#turnstileMount");
  if (!button || !mount) return;
  button.disabled = true;
  button.dataset.locked = "true";
  setStatus(messages.loading);
  try {
    const configResponse = await fetch("/api/contact-config", { cache: "no-store" });
    const config = await configResponse.json();
    if (!configResponse.ok || !config?.configured || typeof config.sitekey !== "string" || !config.sitekey) {
      throw new Error("contact verification is not configured");
    }
    const turnstile = await loadTurnstile();
    mount.hidden = false;
    let widgetId = null;
    widgetId = turnstile.render(mount, {
      sitekey: config.sitekey,
      theme: "dark",
      size: "flexible",
      appearance: "interaction-only",
      action: "contact_reveal",
      callback: (token) => submitToken(token, turnstile, widgetId),
      "error-callback": () => setStatus(messages.failed, "error"),
      "expired-callback": () => turnstile.reset(widgetId)
    });
  } catch {
    setStatus(messages.unavailable, "error");
    button.disabled = false;
    delete button.dataset.locked;
    refreshContactCopy();
  }
}

function init() {
  enhanceSkillIcons();
  refreshContactCopy();
  const button = document.querySelector("#contactReveal");
  button?.addEventListener("click", startContactVerification);
  new MutationObserver(refreshContactCopy).observe(document.documentElement, { attributes: true, attributeFilter: ["lang"] });
}

if (typeof document !== "undefined") {
  window.addEventListener("DOMContentLoaded", init, { once: true });
}
