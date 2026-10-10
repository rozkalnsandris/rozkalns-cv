import { localeFor } from "../core/i18n.mjs";

export const REQUIRED_STATS = Object.freeze([
  "updated", "uptime_30d", "docker_containers", "load1", "days_online",
  "cpu_usage", "ram_usage", "disk_usage", "cpu_temp"
]);

export function validateStats(payload, nowMs = Date.now()) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return { valid: false, state: "unavailable", reason: "shape" };
  }
  for (const key of REQUIRED_STATS) {
    if (!(key in payload)) return { valid: false, state: "unavailable", reason: `missing:${key}` };
  }
  const timestamp = Date.parse(payload.updated);
  if (!Number.isFinite(timestamp)) {
    return { valid: false, state: "unavailable", reason: "timestamp" };
  }
  const ageMinutes = (nowMs - timestamp) / 60000;
  if (!Number.isFinite(ageMinutes) || ageMinutes < -5) {
    return { valid: false, state: "unavailable", reason: "future" };
  }
  for (const [key, value] of Object.entries(payload)) {
    if (key === "updated") continue;
    if (value !== null && (typeof value !== "number" || !Number.isFinite(value))) {
      return { valid: false, state: "unavailable", reason: `number:${key}` };
    }
  }
  return {
    valid: true,
    state: ageMinutes > 15 ? "stale" : "fresh",
    ageMinutes,
    timestamp
  };
}

function setStatus(state, messages, root) {
  const dots = [
    root.querySelector?.("#liveDot"),
    ...Array.from(root.querySelectorAll?.("[data-live-state-dot]") || [])
  ].filter(Boolean);
  const labels = [
    root.querySelector?.("#liveLabel"),
    ...Array.from(root.querySelectorAll?.("[data-live-state-label]") || [])
  ].filter(Boolean);
  if (!dots.length || !labels.length) return;
  const key = state === "fresh" ? "status_fresh"
    : state === "stale" ? "status_stale"
    : state === "loading" ? "status_loading"
    : "status_unavailable";
  const text = messages?.[key] || {
    fresh: "metrics updated",
    stale: "metrics delayed",
    loading: "checking metrics",
    unavailable: "metrics unavailable"
  }[state];
  dots.forEach((dot) => {
    if (dot.dataset.state !== state) dot.dataset.state = state;
  });
  // An unchanged status must not cause another screen-reader announcement.
  labels.forEach((label) => {
    if (label.textContent !== text) label.textContent = text;
  });
}

function clearStats(root) {
  root.querySelectorAll("[data-stat]").forEach((element) => {
    if (element.textContent !== "—") element.textContent = "—";
  });
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
  let loadGeneration = 0;

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
      clearStats(root);
      setStatus("unavailable", languageController.messages, root);
      const updated = root.querySelector("#statsUpdated");
      if (updated) updated.textContent = "—";
    }
    return true;
  }

  async function load() {
    const generation = ++loadGeneration;
    if (!renderState) setStatus("loading", languageController.messages, root);
    try {
      const response = await fetchImpl(`/stats.json?_=${Date.now()}`, { cache: "no-store" });
      if (!response.ok) throw new Error("stats unavailable");
      const payload = await response.json();
      const validation = validateStats(payload);
      if (!validation.valid) throw new Error(validation.reason);
      if (generation !== loadGeneration) return;
      renderState = { kind: "data", payload, validation };
      rerender();
    } catch {
      if (generation !== loadGeneration) return;
      renderState = { kind: "unavailable" };
      rerender();
    }
  }

  function start() {
    windowLike.clearInterval(timer);
    load();
    timer = windowLike.setInterval(load, 60000);
  }

  function stop() {
    loadGeneration += 1;
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
