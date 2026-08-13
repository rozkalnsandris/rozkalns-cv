import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";
import {
  createLanguageController,
  localeFor,
  normalizeLanguage,
  preferredLanguage
} from "../frontend/core/i18n.mjs";
import { createTurnstileLoader } from "../frontend/core/turnstile.mjs";
import {
  buildChatPayload,
  normalizeCompletedHistory
} from "../frontend/features/chat.mjs";
import { contactPayloadIsValid, contactPurpose } from "../frontend/features/contact.mjs";
import {
  bindStatsVisibility,
  createStatsController,
  validateStats
} from "../frontend/features/stats.mjs";
import { skillIconName } from "../frontend/ui/icons.mjs";

const ROOT = resolve(import.meta.dirname, "..");
const liveStats = {
  updated: "2026-08-06T12:00:00Z",
  uptime_30d: 99.9,
  docker_containers: 12,
  load1: 0.25,
  days_online: 9,
  cpu_usage: 14.2,
  ram_usage: 47.1,
  disk_usage: 35.4,
  cpu_temp: 52.3
};

test("shared locale core preserves cvlang preference and fallback semantics", () => {
  const storage = { getItem: (key) => key === "cvlang" ? "lv" : null };
  assert.equal(preferredLanguage({ storage, navigatorLike: { language: "de-DE" } }), "lv");
  assert.equal(
    preferredLanguage({ storage: { getItem: () => null }, navigatorLike: { language: "de-DE" } }),
    "de"
  );
  assert.equal(normalizeLanguage("fr-FR"), "en");
  assert.equal(localeFor("lv"), "lv-LV");
  assert.equal(localeFor("de"), "de-DE");
  assert.equal(localeFor("en"), "en-GB");
});

test("language switching contains load failures, preserves state, and remains retryable", async () => {
  const root = {
    documentElement: { lang: "en" },
    querySelectorAll() { return []; },
    querySelector() { return null; }
  };
  const storage = {
    value: "en",
    getItem(key) { return key === "cvlang" ? this.value : null; },
    setItem(key, value) { if (key === "cvlang") this.value = value; }
  };
  let attempt = 0;
  const fetchImpl = async () => {
    attempt += 1;
    if (attempt === 1) {
      return { ok: true, async json() { return { label: "English" }; } };
    }
    if (attempt === 2) {
      return { ok: false, async json() { return {}; } };
    }
    return { ok: true, async json() { return { label: "Deutsch" }; } };
  };
  const controller = createLanguageController({
    root,
    storage,
    navigatorLike: { language: "en-GB" },
    fetchImpl
  });

  assert.equal(await controller.tryApply("en"), true);
  const previousMessages = controller.messages;
  assert.equal(controller.language, "en");
  assert.equal(storage.value, "en");

  await assert.doesNotReject(() => controller.tryApply("de"));
  assert.equal(await controller.tryApply("de"), true);
  assert.equal(controller.language, "de");
  assert.deepEqual(controller.messages, { label: "Deutsch" });
  assert.equal(root.documentElement.lang, "de");
  assert.equal(storage.value, "de");
  assert.notEqual(controller.messages, previousMessages);
});

test("failed language switch leaves the previously applied state unchanged", async () => {
  const root = {
    documentElement: { lang: "en" },
    querySelectorAll() { return []; },
    querySelector() { return null; }
  };
  const storage = {
    value: "en",
    getItem() { return this.value; },
    setItem(_key, value) { this.value = value; }
  };
  let fail = false;
  const fetchImpl = async () => {
    if (fail) return { ok: false, async json() { return {}; } };
    return { ok: true, async json() { return { label: "English" }; } };
  };
  const controller = createLanguageController({
    root,
    storage,
    navigatorLike: { language: "en-GB" },
    fetchImpl
  });

  assert.equal(await controller.tryApply("en"), true);
  const previousMessages = controller.messages;
  fail = true;

  assert.equal(await controller.tryApply("de"), false);
  assert.equal(controller.language, "en");
  assert.equal(controller.messages, previousMessages);
  assert.equal(root.documentElement.lang, "en");
  assert.equal(storage.value, "en");
});

test("latest language request wins when responses complete out of order", async () => {
  const root = {
    documentElement: { lang: "en" },
    querySelectorAll() { return []; },
    querySelector() { return null; }
  };
  const storage = {
    value: "en",
    getItem() { return this.value; },
    setItem(_key, value) { this.value = value; }
  };
  const pending = new Map();
  const applied = [];
  const fetchImpl = async (url) => {
    const language = ["en", "de", "lv"].find((candidate) => String(url).endsWith(`/${candidate}.json`));
    assert.ok(language, `unexpected translation URL: ${url}`);
    if (language === "en") {
      return { ok: true, async json() { return { label: "English" }; } };
    }
    return new Promise((resolveResponse) => pending.set(language, resolveResponse));
  };
  const controller = createLanguageController({
    root,
    storage,
    navigatorLike: { language: "en-GB" },
    fetchImpl,
    onApplied(state) { applied.push({ language: state.language, messages: state.messages }); }
  });

  assert.equal(await controller.tryApply("en"), true);
  const de = controller.tryApply("de");
  const lv = controller.tryApply("lv");
  assert.equal(pending.has("de"), true);
  assert.equal(pending.has("lv"), true);

  pending.get("lv")({ ok: true, async json() { return { label: "Latviešu" }; } });
  assert.equal(await lv, true);
  assert.equal(controller.language, "lv");
  assert.deepEqual(controller.messages, { label: "Latviešu" });
  assert.equal(root.documentElement.lang, "lv");
  assert.equal(storage.value, "lv");
  assert.deepEqual(applied.map((state) => state.language), ["en", "lv"]);

  pending.get("de")({ ok: true, async json() { return { label: "Deutsch" }; } });
  assert.equal(await de, true);
  assert.equal(controller.language, "lv");
  assert.deepEqual(controller.messages, { label: "Latviešu" });
  assert.equal(root.documentElement.lang, "lv");
  assert.equal(storage.value, "lv");
  assert.deepEqual(applied.map((state) => state.language), ["en", "lv"]);
});

test("contact copy lives in canonical translation documents", async () => {
  const keys = [
    "contact_reveal",
    "contact_whatsapp_verify",
    "contact_loading",
    "contact_verifying",
    "contact_success",
    "contact_failed",
    "contact_unavailable",
    "contact_email_hidden",
    "contact_phone_hidden"
  ];
  for (const language of ["en", "de", "lv"]) {
    const document = JSON.parse(
      await readFile(resolve(ROOT, `content/translations/${language}.json`), "utf8")
    );
    for (const key of keys) assert.equal(typeof document[key], "string", `${language}:${key}`);
  }
  const compatibility = await readFile(resolve(ROOT, "frontend/enhancements.mjs"), "utf8");
  assert.doesNotMatch(compatibility, /const\s+TEXT\s*=/);
});

test("chat payload contains the current question once", () => {
  const history = [
    { role: "user", content: "previous" },
    { role: "assistant", content: "answer" }
  ];
  const payload = buildChatPayload("current", history);
  assert.equal(payload.message, "current");
  assert.deepEqual(payload.history, history);
  assert.equal(JSON.stringify(payload).match(/current/g)?.length, 1);
});

test("incomplete history is dropped", () => {
  const history = [
    { role: "user", content: "complete" },
    { role: "assistant", content: "answer" },
    { role: "user", content: "orphan" }
  ];
  assert.deepEqual(normalizeCompletedHistory(history), history.slice(0, 2));
});

test("Turnstile script loading is shared in flight and retryable after failure", async () => {
  const scripts = [];
  const root = {
    createElement(tagName) {
      assert.equal(tagName, "script");
      const listeners = new Map();
      return {
        src: "",
        async: false,
        defer: false,
        removed: false,
        addEventListener(type, listener) { listeners.set(type, listener); },
        remove() { this.removed = true; },
        dispatch(type) { listeners.get(type)?.(); }
      };
    },
    head: {
      append(script) { scripts.push(script); }
    }
  };
  const windowLike = {};
  const loadTurnstile = createTurnstileLoader();

  const first = loadTurnstile(root, windowLike);
  const concurrent = loadTurnstile(root, windowLike);
  assert.equal(first, concurrent);
  assert.equal(scripts.length, 1);
  assert.equal(
    scripts[0].src,
    "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit"
  );
  assert.equal(scripts[0].async, true);
  assert.equal(scripts[0].defer, true);

  scripts[0].dispatch("error");
  await assert.rejects(first, /turnstile unavailable/);
  assert.equal(scripts[0].removed, true);

  const second = loadTurnstile(root, windowLike);
  assert.notEqual(second, first);
  assert.equal(scripts.length, 2);

  const api = { render() {} };
  windowLike.turnstile = api;
  scripts[1].dispatch("load");
  assert.equal(await second, api);
  assert.equal(await loadTurnstile(root, windowLike), api);
  assert.equal(scripts.length, 2);
});

test("valid recent stats are live", () => {
  const result = validateStats(liveStats, Date.parse("2026-08-06T12:05:00Z"));
  assert.equal(result.valid, true);
  assert.equal(result.state, "live");
});

test("old stats are stale", () => {
  const result = validateStats(liveStats, Date.parse("2026-08-06T12:20:01Z"));
  assert.equal(result.valid, true);
  assert.equal(result.state, "stale");
});

test("future, malformed, and non-finite stats are offline", () => {
  assert.equal(
    validateStats(liveStats, Date.parse("2026-08-06T11:50:00Z")).valid,
    false
  );
  assert.equal(validateStats({ ...liveStats, updated: "bad" }).valid, false);
  assert.equal(validateStats({ ...liveStats, load1: Number.NaN }).valid, false);
  const missing = { ...liveStats };
  delete missing.cpu_temp;
  assert.equal(validateStats(missing).valid, false);
});

test("stats polling follows initial and changing page visibility", () => {
  const calls = [];
  const documentListeners = new Map();
  const windowListeners = new Map();
  const documentLike = {
    hidden: true,
    addEventListener(type, listener) { documentListeners.set(type, listener); },
    removeEventListener(type, listener) {
      if (documentListeners.get(type) === listener) documentListeners.delete(type);
    }
  };
  const windowLike = {
    addEventListener(type, listener) { windowListeners.set(type, listener); },
    removeEventListener(type, listener) {
      if (windowListeners.get(type) === listener) windowListeners.delete(type);
    }
  };
  const stats = {
    start() { calls.push("start"); },
    stop() { calls.push("stop"); }
  };

  const cleanup = bindStatsVisibility(stats, { documentLike, windowLike });
  assert.deepEqual(calls, ["stop"]);

  documentLike.hidden = false;
  documentListeners.get("visibilitychange")();
  documentLike.hidden = true;
  documentListeners.get("visibilitychange")();
  windowListeners.get("pagehide")();
  assert.deepEqual(calls, ["stop", "start", "stop", "stop"]);

  cleanup();
  assert.equal(documentListeners.has("visibilitychange"), false);
  assert.equal(windowListeners.has("pagehide"), false);
  assert.deepEqual(calls, ["stop", "start", "stop", "stop", "stop"]);
});

test("hidden stats polling has no recurring fetch and visible restore refreshes immediately", () => {
  let fetches = 0;
  let interval = null;
  const documentListeners = new Map();
  const windowListeners = new Map();
  const documentLike = {
    hidden: false,
    addEventListener(type, listener) { documentListeners.set(type, listener); },
    removeEventListener(type, listener) {
      if (documentListeners.get(type) === listener) documentListeners.delete(type);
    }
  };
  const windowLike = {
    clearInterval() { interval = null; },
    setInterval(callback) { interval = callback; return 1; },
    addEventListener(type, listener) { windowListeners.set(type, listener); },
    removeEventListener(type, listener) {
      if (windowListeners.get(type) === listener) windowListeners.delete(type);
    }
  };
  const root = {
    querySelector() { return null; },
    querySelectorAll() { return []; }
  };
  const fetchImpl = async () => {
    fetches += 1;
    return {
      ok: true,
      async json() { return { ...liveStats, updated: new Date().toISOString() }; }
    };
  };
  const languageController = { language: "en", messages: {} };
  const stats = createStatsController(languageController, { root, fetchImpl, windowLike });
  const cleanup = bindStatsVisibility(stats, { documentLike, windowLike });

  assert.equal(fetches, 1);
  assert.equal(typeof interval, "function");

  documentLike.hidden = true;
  documentListeners.get("visibilitychange")();
  assert.equal(fetches, 1);
  assert.equal(interval, null);

  documentLike.hidden = false;
  documentListeners.get("visibilitychange")();
  assert.equal(fetches, 2);
  assert.equal(typeof interval, "function");

  cleanup();
  assert.equal(interval, null);
});

test("cached stats rerender in the applied language without refetching", async () => {
  let fetches = 0;
  let unavailable = false;
  const dot = { dataset: {} };
  const label = { textContent: "" };
  const updated = { textContent: "" };
  const root = {
    querySelector(selector) {
      if (selector === "#liveDot") return dot;
      if (selector === "#liveLabel") return label;
      if (selector === "#statsUpdated") return updated;
      return null;
    },
    querySelectorAll() { return []; }
  };
  const fetchImpl = async () => {
    fetches += 1;
    if (unavailable) return { ok: false, async json() { return {}; } };
    return {
      ok: true,
      async json() { return { ...liveStats, updated: new Date().toISOString() }; }
    };
  };
  const languageController = {
    language: "en",
    messages: {
      status_live: "Live",
      status_offline: "Offline",
      last_update: "Last update"
    }
  };
  const stats = createStatsController(languageController, {
    root,
    fetchImpl,
    windowLike: { clearInterval() {}, setInterval() { return 1; } }
  });

  await stats.load();
  assert.equal(fetches, 1);
  assert.equal(label.textContent, "Live");
  assert.match(updated.textContent, /^Last update:/);

  languageController.language = "de";
  languageController.messages = {
    status_live: "Aktuell",
    status_offline: "Nicht verfügbar",
    last_update: "Letzte Aktualisierung"
  };
  assert.equal(stats.rerender(), true);
  assert.equal(fetches, 1);
  assert.equal(label.textContent, "Aktuell");
  assert.match(updated.textContent, /^Letzte Aktualisierung:/);

  unavailable = true;
  await stats.load();
  assert.equal(fetches, 2);
  assert.equal(label.textContent, "Nicht verfügbar");
  assert.equal(updated.textContent, "—");

  languageController.language = "lv";
  languageController.messages = {
    status_live: "Tiešsaistē",
    status_offline: "Bezsaistē",
    last_update: "Pēdējais atjauninājums"
  };
  assert.equal(stats.rerender(), true);
  assert.equal(fetches, 2);
  assert.equal(label.textContent, "Bezsaistē");
  assert.equal(updated.textContent, "—");
});

test("chat and contact stay behind interaction-only dynamic imports", async () => {
  const source = await readFile(resolve(ROOT, "frontend/app.mjs"), "utf8");
  assert.doesNotMatch(source, /^import[\s\S]*?from "\.\/features\/chat\.mjs";/m);
  assert.doesNotMatch(source, /^import[\s\S]*?from "\.\/features\/contact\.mjs";/m);
  assert.match(source, /import\("\.\/features\/chat\.mjs"\)/);
  assert.match(source, /import\("\.\/features\/contact\.mjs"\)/);
  assert.match(source, /from "\.\/features\/stats\.mjs";/);
  assert.match(source, /bindStatsVisibility\(stats\)/);
  assert.match(source, /if \(applied\) stats\.rerender\(\);/);
});

test("page entrypoints use contained language switching only", async () => {
  for (const sourcePath of ["frontend/app.mjs", "frontend/smarthome.mjs"]) {
    const source = await readFile(resolve(ROOT, sourcePath), "utf8");
    assert.match(source, /languageController\.tryApply\(button\.dataset\.lang\)/, sourcePath);
    assert.doesNotMatch(source, /languageController\.apply\(/, sourcePath);
  }
});

test("skill chips map to meaningful SVG icon families", () => {
  assert.equal(skillIconName("Docker Compose"), "container");
  assert.equal(skillIconName("SSL/TLS"), "shield");
  assert.equal(skillIconName("Prometheus"), "chart");
  assert.equal(skillIconName("Home Assistant"), "home");
  assert.equal(skillIconName("ESP32 / IoT"), "chip");
  assert.equal(skillIconName("Terraform"), "cloud");
});

test("contact reveal payload must contain bounded contact shapes", () => {
  assert.equal(
    contactPayloadIsValid({
      email: "person@example.com",
      phone: "+49 123 456789",
      phone_uri: "+49123456789"
    }),
    true
  );
  assert.equal(
    contactPayloadIsValid({
      email: "not-an-email",
      phone: "123",
      phone_uri: "invalid-phone-uri"
    }),
    false
  );
  assert.equal(
    contactPurpose({ location: { href: "https://rozkalns.net/?contact=whatsapp" } }),
    "whatsapp"
  );
});