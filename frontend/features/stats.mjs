import { localeFor } from "../core/i18n.mjs";

export const REQUIRED_STATS = Object.freeze([
  "updated", "uptime_30d", "docker_containers", "load1", "days_online",
  "cpu_usage", "ram_usage", "disk_usage", "cpu_temp"
]);

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

function setStatus(state, messages, root) {
  const dot = root.querySelector("#liveDot");
  const label = root.querySelector("#liveLabel");
  if (!dot || !label) return;
  dot.dataset.state = state;
  const key = state === "live" ? "status_live" : state === "stale" ? "status_stale" : "status_offline";
  label.textContent = messages?.[key] || state;
}

function renderStats(payload, validation, language, messages, root) {
  root.querySelectorAll("[data-stat]").forEach((element) => {
    const value = payload[element.dataset.stat];
    if (value === null || value === undefined) {
      element.textContent = "—";
      return;
    }
    const decimals = Number.parseInt(element.dataset.decimals || "0", 10);
    const suffix = element.dataset.suffix || "";
    element.textContent = `${Number(value).toFixed(decimals)}${suffix}`;
  });
  const stamp = new Date(validation.timestamp).toLocaleString(localeFor(language), {
    day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit"
  });
  const updated = root.querySelector("#statsUpdated");
  if (updated) updated.textContent = `${messages?.last_update || "Last update"}: ${stamp}`;
  setStatus(validation.state, messages, root);
}

export function createStatsController(languageController, {
  root = globalThis.document,
  fetchImpl = globalThis.fetch,
  windowLike = globalThis.window
} = {}) {
  let timer = null;
  let renderState = null;

  function rerender() {
    if (!renderState) return false;
    if (renderState.kind === "data") {
      renderStats(
        renderState.payload,
        renderState.validation,
        languageController.language,
        languageController.messages,
        root
      );
    } else {
      setStatus("offline", languageController.messages, root);
      const updated = root.querySelector("#statsUpdated");
      if (updated) updated.textContent = "—";
    }
    return true;
  }

  async function load() {
    try {
      const response = await fetchImpl(`/stats.json?_=${Date.now()}`, { cache: "no-store" });
      if (!response.ok) throw new Error("stats unavailable");
      const payload = await response.json();
      const validation = validateStats(payload);
      if (!validation.valid) throw new Error(validation.reason);
      renderState = { kind: "data", payload, validation };
      rerender();
    } catch {
      renderState = { kind: "offline" };
      rerender();
    }
  }

  function start() {
    windowLike.clearInterval(timer);
    load();
    timer = windowLike.setInterval(load, 60000);
  }

  function stop() {
    windowLike.clearInterval(timer);
    timer = null;
  }

  return { load, rerender, start, stop };
}

export function bindStatsVisibility(statsController, {
  documentLike = globalThis.document,
  windowLike = globalThis.window
} = {}) {
  const sync = () => {
    if (documentLike.hidden) statsController.stop();
    else statsController.start();
  };
  const stop = () => statsController.stop();
  const restore = (event) => {
    if (event?.persisted === true) sync();
  };

  sync();
  documentLike.addEventListener("visibilitychange", sync);
  windowLike.addEventListener("pagehide", stop);
  windowLike.addEventListener("pageshow", restore);

  return () => {
    documentLike.removeEventListener("visibilitychange", sync);
    windowLike.removeEventListener("pagehide", stop);
    windowLike.removeEventListener("pageshow", restore);
    statsController.stop();
  };
}
