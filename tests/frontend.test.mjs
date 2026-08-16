import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";
import { installPreloadErrorRecovery, updateChatLauncherLabel, updateMainDocumentTitle } from "../frontend/app.mjs";
import {
  applyRegionDisplayNames,
  applySkillTranslations,
  createLanguageController,
  localeFor,
  normalizeLanguage,
  preferredLanguage,
  regionDisplayName
} from "../frontend/core/i18n.mjs";
import { createTurnstileLoader, turnstileLanguage } from "../frontend/core/turnstile.mjs";
import {
  buildChatPayload,
  chatStreamSucceeded,
  createChatController,
  normalizeCompletedHistory
} from "../frontend/features/chat.mjs";
import {
  createContactController,
  contactPayloadIsValid,
  contactPurpose
} from "../frontend/features/contact.mjs";
import {
  bindStatsVisibility,
  createStatsController,
  validateStats
} from "../frontend/features/stats.mjs";
import { enhanceSkillIcons, skillIconName } from "../frontend/ui/icons.mjs";

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

test("Vite preload recovery reloads a stale document at most once", async () => {
  const listeners = new Map();
  let reloads = 0;

  const windowLike = {
    addEventListener(type, listener) {
      listeners.set(type, listener);
    },
    location: {
      reload() {
        reloads += 1;
      }
    }
  };

  const recover = installPreloadErrorRecovery(windowLike);

  assert.equal(typeof recover, "function");
  assert.equal(listeners.has("vite:preloadError"), true);

  let prevented = 0;
  const event = {
    preventDefault() {
      prevented += 1;
    }
  };

  assert.equal(listeners.get("vite:preloadError")(event), true);
  assert.equal(listeners.get("vite:preloadError")(event), false);

  assert.equal(prevented, 2);
  assert.equal(reloads, 1);

  assert.equal(installPreloadErrorRecovery({}), null);

  const source = await readFile(
    resolve(ROOT, "frontend/app.mjs"),
    "utf8"
  );

  assert.match(
    source,
    /installPreloadErrorRecovery\(window\);\s*window\.addEventListener\("DOMContentLoaded"/
  );
});

test("chat launcher uses descriptive responsive translated labels", () => {
  const launcher = { textContent: "" };
  const documentLike = { querySelector: (selector) => selector === "#chatLauncher" ? launcher : null };
  const messages = { chat_open: "Ask the CV assistant", chat_title: "CV assistant" };

  assert.equal(updateChatLauncherLabel({ messages }, { documentLike, viewportWidth: 639 }), true);
  assert.equal(launcher.textContent, "Ask the CV assistant");
  updateChatLauncherLabel({ messages }, { documentLike, viewportWidth: 720 });
  assert.equal(launcher.textContent, "CV assistant");
  updateChatLauncherLabel({ messages }, { documentLike, viewportWidth: 1559 });
  assert.equal(launcher.textContent, "CV assistant");
  updateChatLauncherLabel({ messages }, { documentLike, viewportWidth: 1560 });
  assert.equal(launcher.textContent, "Ask the CV assistant");
  assert.equal(updateChatLauncherLabel({ messages }, { documentLike: {}, viewportWidth: 900 }), false);
});

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

test("profile location uses semantic region data and locale display names", async () => {
  const source = await readFile(resolve(ROOT, "frontend/index.html"), "utf8");
  assert.match(
    source,
    /id="profileLocation" data-city="Dortmund" data-region-code="DE">Dortmund, Germany<\/span>/
  );

  const expected = new Map([
    ["en-GB", "Germany"],
    ["de-DE", "Deutschland"],
    ["lv-LV", "Vācija"]
  ]);
  class FakeDisplayNames {
    constructor(locales, options) {
      this.locale = locales[0];
      assert.deepEqual(options, { type: "region", fallback: "code" });
    }
    of(code) {
      assert.equal(code, "DE");
      return expected.get(this.locale);
    }
  }

  assert.equal(regionDisplayName("DE", "en", { DisplayNames: FakeDisplayNames }), "Germany");
  assert.equal(regionDisplayName("DE", "de", { DisplayNames: FakeDisplayNames }), "Deutschland");
  assert.equal(regionDisplayName("DE", "lv", { DisplayNames: FakeDisplayNames }), "Vācija");
  assert.equal(regionDisplayName("DE", "lv", { DisplayNames: null }), "DE");
  assert.equal(regionDisplayName("not-a-region", "de", { DisplayNames: FakeDisplayNames }), "NOT-A-REGION");

  class BrokenDisplayNames {
    constructor() { throw new Error("missing locale data"); }
  }
  assert.equal(regionDisplayName("DE", "de", { DisplayNames: BrokenDisplayNames }), "DE");

  const location = {
    dataset: { city: "Dortmund", regionCode: "DE" },
    textContent: "Dortmund, Germany"
  };
  const root = {
    querySelectorAll(selector) {
      return selector === "[data-region-code]" ? [location] : [];
    }
  };
  applyRegionDisplayNames("de", { root, DisplayNames: FakeDisplayNames });
  assert.equal(location.textContent, "Dortmund, Deutschland");
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
    return { ok: true, async json() { return { label: "English", role: "Junior DevOps & Linux Engineer" }; } };
  };
  const documentLike = { title: "Initial title" };
  const controller = createLanguageController({
    root,
    storage,
    navigatorLike: { language: "en-GB" },
    fetchImpl,
    onApplied(state) { updateMainDocumentTitle(state, { documentLike }); }
  });

  assert.equal(await controller.tryApply("en"), true);
  assert.equal(documentLike.title, "Andris Rožkalns · DevOps & Linux Engineer");
  const previousMessages = controller.messages;
  fail = true;

  assert.equal(await controller.tryApply("de"), false);
  assert.equal(controller.language, "en");
  assert.equal(controller.messages, previousMessages);
  assert.equal(root.documentElement.lang, "en");
  assert.equal(storage.value, "en");
  assert.equal(documentLike.title, "Andris Rožkalns · DevOps & Linux Engineer");
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

test("Smart Home device headings use canonical translations in every language", async () => {
  const source = await readFile(
    resolve(ROOT, "frontend/smarthome.html"),
    "utf8"
  );

  const expected = {
    en: {
      smart_desk_lamp: "Desk lamp",
      smart_air_quality: "Air quality",
      smart_heating_zones: "Heating zones",
      smart_open_windows: "Open windows"
    },
    de: {
      smart_desk_lamp: "Schreibtischlampe",
      smart_air_quality: "Luftqualität",
      smart_heating_zones: "Heizzonen",
      smart_open_windows: "Offene Fenster"
    },
    lv: {
      smart_desk_lamp: "Galda lampa",
      smart_air_quality: "Gaisa kvalitāte",
      smart_heating_zones: "Apkures zonas",
      smart_open_windows: "Atvērtie logi"
    }
  };

  const keys = Object.keys(expected.en);

  for (const key of keys) {
    assert.equal(
      source.includes(`data-i18n="${key}"`),
      true,
      `missing Smart Home i18n binding: ${key}`
    );
  }

  for (const [language, values] of Object.entries(expected)) {
    const document = JSON.parse(
      await readFile(
        resolve(ROOT, `content/translations/${language}.json`),
        "utf8"
      )
    );

    for (const [key, value] of Object.entries(values)) {
      assert.equal(document[key], value, `${language}:${key}`);
    }
  }
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

test("contact status rerenders in the applied language without refetch or reset", async () => {
  const previousMutationObserver = globalThis.MutationObserver;
  const observers = [];
  globalThis.MutationObserver = class {
    constructor(callback) {
      this.callback = callback;
      observers.push(this);
    }
    observe() {}
  };

  try {
    const label = { textContent: "" };
    const status = { textContent: "", dataset: {} };
    const mount = { hidden: true };
    let currentPhone = {
      dataset: {},
      ariaLabel: "",
      setAttribute(name, value) {
        if (name === "aria-label") this.ariaLabel = value;
      },
      replaceWith(link) {
        currentPhone = link;
      }
    };
    const buttonListeners = new Map();
    const button = {
      dataset: {},
      disabled: false,
      hidden: false,
      querySelector(selector) {
        return selector === ".contact-reveal-label" ? label : null;
      },
      addEventListener(type, listener) {
        buttonListeners.set(type, listener);
      },
      removeEventListener(type, listener) {
        if (buttonListeners.get(type) === listener) buttonListeners.delete(type);
      }
    };
    const root = {
      documentElement: {},
      querySelector(selector) {
        if (selector === "#contactReveal") return button;
        if (selector === "#turnstileMount") return mount;
        if (selector === "#contactVerifyStatus") return status;
        if (selector === "#contactPhone") return currentPhone;
        return null;
      },
      createElement(tagName) {
        assert.equal(tagName, "a");
        return {
          dataset: {},
          href: "",
          textContent: "",
          focused: false,
          focus() { this.focused = true; }
        };
      }
    };
    let turnstileOptions = null;
    let resets = 0;
    const windowLike = {
      location: { href: "https://rozkalns.net/" },
      setTimeout(callback) { callback(); },
      turnstile: {
        render(_mount, options) {
          turnstileOptions = options;
          return 17;
        },
        reset(widgetId) {
          assert.equal(widgetId, 17);
          resets += 1;
        }
      }
    };
    let fetches = 0;
    let resolveReveal = null;
    const fetchImpl = async (url) => {
      fetches += 1;
      if (url === "/api/contact-config") {
        return {
          ok: true,
          async json() { return { configured: true, sitekey: "site-key" }; }
        };
      }
      if (url === "/api/contact-reveal") {
        return new Promise((resolveResponse) => { resolveReveal = resolveResponse; });
      }
      throw new Error(`unexpected contact URL: ${url}`);
    };
    const languageController = {
      messages: {
        contact_reveal: "Reveal phone",
        contact_phone_hidden: "Phone hidden",
        contact_loading: "Loading",
        contact_verifying: "Verifying",
        contact_failed: "Failed",
        contact_success: "Success",
        contact_unavailable: "Unavailable"
      }
    };
    const controller = createContactController(languageController, { root, windowLike, fetchImpl });
    assert.ok(controller);
    assert.equal(observers.length, 1);

    const start = controller.start();
    assert.equal(status.textContent, "Loading");
    assert.equal(fetches, 1);

    languageController.messages = {
      contact_reveal: "Telefon anzeigen",
      contact_phone_hidden: "Telefon verborgen",
      contact_loading: "Wird geladen",
      contact_verifying: "Wird geprüft",
      contact_failed: "Fehlgeschlagen",
      contact_success: "Erfolgreich",
      contact_unavailable: "Nicht verfügbar"
    };
    observers[0].callback();
    assert.equal(status.textContent, "Wird geladen");
    assert.equal(fetches, 1);
    assert.equal(resets, 0);

    await start;
    assert.ok(turnstileOptions);
    turnstileOptions["error-callback"]();
    assert.equal(status.textContent, "Fehlgeschlagen");

    languageController.messages = {
      contact_reveal: "Rādīt tālruni",
      contact_phone_hidden: "Tālrunis paslēpts",
      contact_loading: "Ielādē",
      contact_verifying: "Pārbauda",
      contact_failed: "Neizdevās",
      contact_success: "Veiksmīgi",
      contact_unavailable: "Nav pieejams"
    };
    observers[0].callback();
    assert.equal(status.textContent, "Neizdevās");
    assert.equal(fetches, 1);
    assert.equal(resets, 0);

    const verification = turnstileOptions.callback("token");
    assert.equal(status.textContent, "Pārbauda");
    assert.equal(fetches, 2);

    languageController.messages = {
      contact_reveal: "Reveal phone again",
      contact_phone_hidden: "Phone hidden again",
      contact_loading: "Loading again",
      contact_verifying: "Verifying again",
      contact_failed: "Failed again",
      contact_success: "Success again",
      contact_unavailable: "Unavailable again"
    };
    observers[0].callback();
    assert.equal(status.textContent, "Verifying again");
    assert.equal(fetches, 2);
    assert.equal(resets, 0);

    resolveReveal({
      ok: true,
      async json() {
        return {
          email: "person@example.com",
          phone: "+49 123 456789",
          phone_uri: "+49123456789"
        };
      }
    });
    assert.equal(await verification, true);
    assert.equal(status.textContent, "Success again");
    assert.equal(currentPhone.textContent, "+49 123 456789");
    assert.equal(currentPhone.href, "https://wa.me/49123456789");
    assert.equal(currentPhone.dataset.revealed, "true");

    languageController.messages = {
      contact_reveal: "Telefon anzeigen erneut",
      contact_phone_hidden: "Telefon verborgen erneut",
      contact_loading: "Wird erneut geladen",
      contact_verifying: "Wird erneut geprüft",
      contact_failed: "Erneut fehlgeschlagen",
      contact_success: "Erneut erfolgreich",
      contact_unavailable: "Erneut nicht verfügbar"
    };
    observers[0].callback();
    assert.equal(status.textContent, "Erneut erfolgreich");
    assert.equal(fetches, 2);
    assert.equal(resets, 0);
    assert.equal(currentPhone.textContent, "+49 123 456789");
    assert.equal(currentPhone.href, "https://wa.me/49123456789");
  } finally {
    if (previousMutationObserver === undefined) {
      delete globalThis.MutationObserver;
    } else {
      globalThis.MutationObserver = previousMutationObserver;
    }
  }
});

test("contact reveal transport failure resets the challenge and remains retryable", async () => {
  const previousMutationObserver = globalThis.MutationObserver;
  globalThis.MutationObserver = class {
    constructor(callback) {
      this.callback = callback;
    }
    observe() {}
  };

  try {
    const label = { textContent: "" };
    const status = { textContent: "", dataset: {} };
    const mount = { hidden: true };

    let currentPhone = {
      dataset: {},
      setAttribute() {},
      replaceWith(link) {
        currentPhone = link;
      }
    };

    const button = {
      dataset: {},
      disabled: false,
      hidden: false,
      querySelector(selector) {
        return selector === ".contact-reveal-label" ? label : null;
      },
      addEventListener() {}
    };

    const root = {
      documentElement: {},
      querySelector(selector) {
        if (selector === "#contactReveal") return button;
        if (selector === "#turnstileMount") return mount;
        if (selector === "#contactVerifyStatus") return status;
        if (selector === "#contactPhone") return currentPhone;
        return null;
      },
      createElement(tagName) {
        assert.equal(tagName, "a");
        return {
          dataset: {},
          href: "",
          textContent: "",
          focused: false,
          focus() {
            this.focused = true;
          }
        };
      }
    };

    let turnstileOptions = null;
    const resets = [];

    const windowLike = {
      location: { href: "https://rozkalns.net/" },
      setTimeout(callback) {
        callback();
      },
      turnstile: {
        render(_mount, options) {
          turnstileOptions = options;
          return 41;
        },
        reset(widgetId) {
          resets.push(widgetId);
        }
      }
    };

    let revealAttempts = 0;

    const fetchImpl = async (url) => {
      if (url === "/api/contact-config") {
        return {
          ok: true,
          async json() {
            return { configured: true, sitekey: "site-key" };
          }
        };
      }

      if (url === "/api/contact-reveal") {
        revealAttempts += 1;

        if (revealAttempts === 1) {
          throw new TypeError("synthetic network failure");
        }

        return {
          ok: true,
          async json() {
            return {
              email: "person@example.com",
              phone: "+49 123 456789",
              phone_uri: "+49123456789"
            };
          }
        };
      }

      throw new Error(`unexpected URL: ${url}`);
    };

    const languageController = {
      messages: {
        contact_reveal: "Reveal phone",
        contact_phone_hidden: "Phone hidden",
        contact_loading: "Loading",
        contact_verifying: "Verifying",
        contact_failed: "Failed",
        contact_success: "Success",
        contact_unavailable: "Unavailable"
      }
    };

    const controller = createContactController(languageController, {
      root,
      windowLike,
      fetchImpl
    });

    assert.ok(controller);

    await controller.start();

    assert.ok(turnstileOptions);
    assert.equal(mount.hidden, false);

    const failed = await turnstileOptions.callback("first-token");

    assert.equal(failed, false);
    assert.equal(revealAttempts, 1);
    assert.equal(status.textContent, "Failed");
    assert.equal(status.dataset.state, "error");
    assert.deepEqual(resets, [41]);
    assert.equal(button.hidden, false);

    const succeeded = await turnstileOptions.callback("fresh-token");

    assert.equal(succeeded, true);
    assert.equal(revealAttempts, 2);
    assert.equal(status.textContent, "Success");
    assert.equal(status.dataset.state, "success");
    assert.deepEqual(resets, [41]);
    assert.equal(button.hidden, true);
    assert.equal(mount.hidden, true);

    assert.equal(currentPhone.textContent, "+49 123 456789");
    assert.equal(currentPhone.href, "https://wa.me/49123456789");
    assert.equal(currentPhone.dataset.revealed, "true");
  } finally {
    if (previousMutationObserver === undefined) {
      delete globalThis.MutationObserver;
    } else {
      globalThis.MutationObserver = previousMutationObserver;
    }
  }
});

test("current chat status rerenders after language changes without refetching", async () => {
  const observers = [];
  class FakeMutationObserver {
    constructor(callback) {
      this.callback = callback;
      observers.push(this);
    }
    observe() {}
  }

  const formListeners = new Map();
  const form = {
    attributes: {},
    addEventListener(type, listener) {
      formListeners.set(type, listener);
    },
    setAttribute(name, value) {
      this.attributes[name] = value;
    }
  };
  const input = {
    value: "",
    focused: false,
    focus() { this.focused = true; }
  };
  const send = { disabled: false };
  const log = {
    children: [],
    scrollTop: 0,
    scrollHeight: 0,
    append(message) {
      this.children.push(message);
      this.scrollHeight = this.children.length;
    }
  };
  const status = {
    textContent: "",
    after(node) { this.afterNode = node; }
  };

  const root = {
    documentElement: { lang: "en" },
    querySelector(selector) {
      if (selector === "#chatForm") return form;
      if (selector === "#chatInput") return input;
      if (selector === "#chatSend") return send;
      if (selector === "#chatLog") return log;
      if (selector === "#chatStatus") return status;
      return null;
    },
    createElement(tagName) {
      assert.equal(tagName, "div");
      return {
        className: "",
        textContent: "",
        attributes: {},
        removed: false,
        setAttribute(name, value) {
          this.attributes[name] = value;
        },
        remove() {
          this.removed = true;
        }
      };
    }
  };

  let turnstileOptions = null;
  let resets = 0;
  const windowLike = {
    MutationObserver: FakeMutationObserver,
    turnstile: {
      render(_mount, options) {
        turnstileOptions = options;
        return 23;
      },
      reset(widgetId) {
        assert.equal(widgetId, 23);
        resets += 1;
      }
    }
  };

  let fetches = 0;
  let chatMode = "success";
  let resolveChat = null;
  const chatPayloads = [];
  const providerNotices = JSON.parse(
    await readFile(resolve(ROOT, "bot/provider_notices.json"), "utf8")
  );

  const fetchImpl = async (url, options = {}) => {
    fetches += 1;

    if (url === "/api/chat-config") {
      return {
        ok: true,
        async json() {
          return { configured: true, sitekey: "chat-site-key" };
        }
      };
    }

    if (url === "/api/chat-admission") {
      assert.deepEqual(JSON.parse(options.body), { token: "token" });
      return {
        ok: true,
        async json() {
          return { session: "chat-session" };
        }
      };
    }

    if (url === "/api/chat") {
      chatPayloads.push(JSON.parse(options.body));
      if (chatMode === "success") {
        return new Promise((resolveResponse) => {
          resolveChat = resolveResponse;
        });
      }
      if (chatMode === "stream-failure") {
        return new Response(`Partial answer${providerNotices.timeout}`, { status: 200 });
      }

      return {
        ok: false,
        status: 503,
        async json() {
          return { reply: "Synthetic safe failure" };
        }
      };
    }

    throw new Error(`unexpected chat URL: ${url}`);
  };

  const languageController = {
    messages: {
      chat_typing: "Preparing answer",
      chat_complete: "Answer complete",
      chat_error: "Connection issue"
    }
  };

  const controller = createChatController(languageController, {
    root,
    windowLike,
    fetchImpl
  });

  assert.ok(controller);
  assert.equal(observers.length, 1);
  assert.equal(controller.rerender(), false);

  input.value = "Hello";
  const first = formListeners.get("submit")({
    preventDefault() {}
  });

  assert.equal(status.textContent, "Preparing answer");
  assert.equal(form.attributes["aria-busy"], "true");
  assert.equal(log.children.length, 1);
  assert.equal(log.children[0].textContent, "Hello");

  const fetchesWhileTyping = fetches;

  languageController.messages = {
    chat_typing: "Antwort wird vorbereitet",
    chat_complete: "Antwort fertig",
    chat_error: "Verbindungsfehler"
  };

  observers[0].callback();

  assert.equal(status.textContent, "Antwort wird vorbereitet");
  assert.equal(fetches, fetchesWhileTyping);
  assert.equal(resets, 0);
  assert.equal(log.children[0].textContent, "Hello");

  for (let attempt = 0; attempt < 10 && !turnstileOptions; attempt += 1) {
    await Promise.resolve();
  }
  assert.ok(turnstileOptions);

  await turnstileOptions.callback("token");

  for (let attempt = 0; attempt < 10 && !resolveChat; attempt += 1) {
    await Promise.resolve();
  }
  assert.ok(resolveChat);

  resolveChat(new Response("Antwort", { status: 200 }));
  await first;

  assert.equal(status.textContent, "Antwort fertig");
  assert.equal(log.children.length, 2);
  assert.equal(log.children[0].textContent, "Hello");
  assert.equal(log.children[1].textContent, "Antwort");
  assert.deepEqual(controller.completedHistory, [
    { role: "user", content: "Hello" },
    { role: "assistant", content: "Antwort" }
  ]);

  const fetchesAfterSuccess = fetches;

  languageController.messages = {
    chat_typing: "Gatavo atbildi",
    chat_complete: "Atbilde pabeigta",
    chat_error: "Savienojuma kļūda"
  };

  observers[0].callback();

  assert.equal(status.textContent, "Atbilde pabeigta");
  assert.equal(fetches, fetchesAfterSuccess);
  assert.equal(resets, 0);
  assert.equal(log.children[1].textContent, "Antwort");
  assert.deepEqual(controller.completedHistory, [
    { role: "user", content: "Hello" },
    { role: "assistant", content: "Antwort" }
  ]);

  chatMode = "failure";
  input.value = "Fail";

  const second = formListeners.get("submit")({
    preventDefault() {}
  });

  assert.equal(status.textContent, "Gatavo atbildi");

  await second;

  assert.equal(status.textContent, "Savienojuma kļūda");
  assert.equal(log.children.at(-1).textContent, "Synthetic safe failure");
  assert.deepEqual(controller.completedHistory, [
    { role: "user", content: "Hello" },
    { role: "assistant", content: "Antwort" }
  ]);

  chatMode = "stream-failure";
  input.value = "Timeout";
  const streamedFailure = formListeners.get("submit")({
    preventDefault() {}
  });
  await streamedFailure;

  assert.equal(status.textContent, "Savienojuma kļūda");
  assert.equal(log.children.at(-1).textContent, `Partial answer${providerNotices.timeout}`);
  assert.deepEqual(controller.completedHistory, [
    { role: "user", content: "Hello" },
    { role: "assistant", content: "Antwort" }
  ]);
  assert.deepEqual(chatPayloads.at(-1).history, [
    { role: "user", content: "Hello" },
    { role: "assistant", content: "Antwort" }
  ]);

  chatMode = "failure";
  input.value = "After timeout";
  await formListeners.get("submit")({ preventDefault() {} });
  assert.deepEqual(chatPayloads.at(-1).history, [
    { role: "user", content: "Hello" },
    { role: "assistant", content: "Antwort" }
  ]);

  const fetchesAfterFailure = fetches;

  languageController.messages = {
    chat_typing: "Antwort wird erneut vorbereitet",
    chat_complete: "Antwort erneut fertig",
    chat_error: "Erneuter Verbindungsfehler"
  };

  observers[0].callback();

  assert.equal(status.textContent, "Erneuter Verbindungsfehler");
  assert.equal(fetches, fetchesAfterFailure);
  assert.equal(resets, 0);
  assert.equal(log.children.at(-1).textContent, "Synthetic safe failure");
  assert.deepEqual(controller.completedHistory, [
    { role: "user", content: "Hello" },
    { role: "assistant", content: "Antwort" }
  ]);

  const source = await readFile(
    resolve(ROOT, "frontend/features/chat.mjs"),
    "utf8"
  );
  assert.doesNotMatch(
    source,
    /Chat verification is temporarily unavailable|Chat verification failed|stream unavailable/
  );
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

test("provider failure notices are reserved non-completed stream suffixes", async () => {
  const notices = JSON.parse(
    await readFile(resolve(ROOT, "bot/provider_notices.json"), "utf8")
  );
  assert.equal(chatStreamSucceeded("Normal answer"), true);
  assert.equal(chatStreamSucceeded("   "), false);
  for (const [statusName, notice] of Object.entries(notices)) {
    assert.equal(chatStreamSucceeded(notice), false, statusName);
    assert.equal(chatStreamSucceeded(`Partial answer${notice}`), false, statusName);
  }
});

test("active contact Turnstile rerenders only when effective CV language changes", async () => {
  const previousMutationObserver = globalThis.MutationObserver;
  const observers = [];
  globalThis.MutationObserver = class {
    constructor(callback) {
      this.callback = callback;
      observers.push(this);
    }
    observe() {}
  };

  try {
    const label = { textContent: "" };
    const status = { textContent: "", dataset: {} };
    const mount = { hidden: true };
    const phone = { dataset: {}, setAttribute() {} };
    const button = {
      dataset: {},
      disabled: false,
      hidden: false,
      querySelector(selector) {
        return selector === ".contact-reveal-label" ? label : null;
      },
      addEventListener() {},
      removeEventListener() {}
    };
    const root = {
      documentElement: { lang: "en" },
      querySelector(selector) {
        if (selector === "#contactReveal") return button;
        if (selector === "#turnstileMount") return mount;
        if (selector === "#contactVerifyStatus") return status;
        if (selector === "#contactPhone") return phone;
        return null;
      }
    };
    const renders = [];
    const removals = [];
    let nextWidgetId = 1;
    const windowLike = {
      location: { href: "https://rozkalns.net/" },
      turnstile: {
        render(_mount, options) {
          const id = nextWidgetId++;
          renders.push({ id, language: options.language });
          return id;
        },
        remove(widgetId) {
          removals.push(widgetId);
        },
        reset() {}
      }
    };
    let configFetches = 0;
    const fetchImpl = async (url) => {
      assert.equal(url, "/api/contact-config");
      configFetches += 1;
      return {
        ok: true,
        async json() { return { configured: true, sitekey: "site-key" }; }
      };
    };
    const languageController = {
      messages: {
        contact_reveal: "Reveal phone",
        contact_phone_hidden: "Phone hidden",
        contact_loading: "Loading",
        contact_failed: "Failed",
        contact_unavailable: "Unavailable"
      }
    };

    const controller = createContactController(languageController, { root, windowLike, fetchImpl });
    await controller.start();
    assert.deepEqual(renders.map((entry) => entry.language), ["en"]);
    assert.deepEqual(removals, []);
    assert.equal(configFetches, 1);

    root.documentElement.lang = "lv";
    observers[0].callback();
    assert.deepEqual(renders.map((entry) => entry.language), ["en"]);
    assert.deepEqual(removals, []);

    root.documentElement.lang = "de";
    observers[0].callback();
    assert.deepEqual(renders.map((entry) => entry.language), ["en", "de"]);
    assert.deepEqual(removals, [1]);
    assert.equal(configFetches, 1);

    root.documentElement.lang = "lv";
    observers[0].callback();
    assert.deepEqual(renders.map((entry) => entry.language), ["en", "de", "en"]);
    assert.deepEqual(removals, [1, 2]);
    assert.equal(configFetches, 1);
  } finally {
    if (previousMutationObserver === undefined) {
      delete globalThis.MutationObserver;
    } else {
      globalThis.MutationObserver = previousMutationObserver;
    }
  }
});

test("active chat admission Turnstile rerenders without restarting admission", async () => {
  const observers = [];
  class FakeMutationObserver {
    constructor(callback) {
      this.callback = callback;
      observers.push(this);
    }
    observe() {}
  }

  const formListeners = new Map();
  const form = {
    attributes: {},
    addEventListener(type, listener) { formListeners.set(type, listener); },
    setAttribute(name, value) { this.attributes[name] = value; }
  };
  const input = { value: "Hello", focus() {} };
  const send = { disabled: false };
  const log = {
    children: [],
    scrollTop: 0,
    scrollHeight: 0,
    append(message) {
      this.children.push(message);
      this.scrollHeight = this.children.length;
    }
  };
  const status = {
    textContent: "",
    after(node) { this.mount = node; }
  };
  const root = {
    documentElement: { lang: "en" },
    querySelector(selector) {
      if (selector === "#chatForm") return form;
      if (selector === "#chatInput") return input;
      if (selector === "#chatSend") return send;
      if (selector === "#chatLog") return log;
      if (selector === "#chatStatus") return status;
      return null;
    },
    createElement(tagName) {
      assert.equal(tagName, "div");
      return {
        className: "",
        textContent: "",
        attributes: {},
        removed: false,
        setAttribute(name, value) { this.attributes[name] = value; },
        remove() { this.removed = true; }
      };
    }
  };
  const renders = [];
  const removals = [];
  let latestOptions = null;
  let nextWidgetId = 11;
  const windowLike = {
    MutationObserver: FakeMutationObserver,
    turnstile: {
      render(_mount, options) {
        const id = nextWidgetId++;
        latestOptions = options;
        renders.push({ id, language: options.language });
        return id;
      },
      remove(widgetId) { removals.push(widgetId); },
      reset() {}
    }
  };
  let configFetches = 0;
  const fetchImpl = async (url) => {
    assert.equal(url, "/api/chat-config");
    configFetches += 1;
    return {
      ok: true,
      async json() { return { configured: true, sitekey: "chat-site-key" }; }
    };
  };
  const languageController = {
    messages: {
      chat_typing: "Preparing answer",
      chat_complete: "Answer complete",
      chat_error: "Connection issue"
    }
  };

  createChatController(languageController, { root, windowLike, fetchImpl });
  const submit = formListeners.get("submit")({ preventDefault() {} });
  for (let attempt = 0; attempt < 10 && renders.length === 0; attempt += 1) {
    await Promise.resolve();
  }
  assert.deepEqual(renders.map((entry) => entry.language), ["en"]);
  assert.deepEqual(removals, []);
  assert.equal(configFetches, 1);

  root.documentElement.lang = "lv";
  observers[0].callback();
  assert.deepEqual(renders.map((entry) => entry.language), ["en"]);
  assert.deepEqual(removals, []);

  root.documentElement.lang = "de";
  observers[0].callback();
  assert.deepEqual(renders.map((entry) => entry.language), ["en", "de"]);
  assert.deepEqual(removals, [11]);
  assert.equal(configFetches, 1);

  root.documentElement.lang = "lv";
  observers[0].callback();
  assert.deepEqual(renders.map((entry) => entry.language), ["en", "de", "en"]);
  assert.deepEqual(removals, [11, 12]);
  assert.equal(configFetches, 1);

  latestOptions["error-callback"]();
  await submit;
  const renderCount = renders.length;
  root.documentElement.lang = "de";
  observers[0].callback();
  assert.equal(renders.length, renderCount);
  assert.equal(configFetches, 1);
});

test("Turnstile widgets follow selected CV language with deterministic fallback", async () => {
  assert.equal(turnstileLanguage("en"), "en");
  assert.equal(turnstileLanguage("en-GB"), "en");
  assert.equal(turnstileLanguage("de"), "de");
  assert.equal(turnstileLanguage("de-DE"), "de");
  assert.equal(turnstileLanguage("lv"), "en");
  assert.equal(turnstileLanguage("fr"), "en");
  assert.equal(turnstileLanguage(undefined), "en");

  const turnstileCore = await readFile(
    resolve(ROOT, "frontend/core/turnstile.mjs"),
    "utf8"
  );
  assert.match(turnstileCore, /createLocalizedTurnstileRenderer/);
  assert.match(turnstileCore, /turnstileLanguage\(root\?\.documentElement\?\.lang\)/);
  assert.match(turnstileCore, /turnstile\.remove\(widgetId\)/);

  for (const path of [
    "frontend/features/contact.mjs",
    "frontend/features/chat.mjs"
  ]) {
    const source = await readFile(resolve(ROOT, path), "utf8");
    assert.match(source, /createLocalizedTurnstileRenderer/, path);
  }
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

test("stats polling follows visibility and repeated bfcache lifecycle", () => {
  const calls = [];
  const documentListeners = new Map();
  const windowListeners = new Map();

  const documentLike = {
    hidden: true,
    addEventListener(type, listener) {
      documentListeners.set(type, listener);
    },
    removeEventListener(type, listener) {
      if (documentListeners.get(type) === listener) {
        documentListeners.delete(type);
      }
    }
  };

  const windowLike = {
    addEventListener(type, listener, options) {
      windowListeners.set(type, { listener, options });
    },
    removeEventListener(type, listener) {
      if (windowListeners.get(type)?.listener === listener) {
        windowListeners.delete(type);
      }
    }
  };

  const stats = {
    start() { calls.push("start"); },
    stop() { calls.push("stop"); }
  };

  const cleanup = bindStatsVisibility(stats, {
    documentLike,
    windowLike
  });

  assert.deepEqual(calls, ["stop"]);
  assert.equal(typeof windowListeners.get("pagehide")?.listener, "function");
  assert.equal(typeof windowListeners.get("pageshow")?.listener, "function");
  assert.notEqual(windowListeners.get("pagehide")?.options?.once, true);

  // Initial/non-bfcache pageshow must not duplicate startup work.
  windowListeners.get("pageshow").listener({ persisted: false });
  assert.deepEqual(calls, ["stop"]);

  // Normal visibility restore starts polling.
  documentLike.hidden = false;
  documentListeners.get("visibilitychange")();
  assert.deepEqual(calls, ["stop", "start"]);

  // First bfcache cycle.
  windowListeners.get("pagehide").listener({ persisted: true });
  windowListeners.get("pageshow").listener({ persisted: true });
  assert.deepEqual(calls, ["stop", "start", "stop", "start"]);

  // Second cycle proves pagehide was not registered once-only.
  windowListeners.get("pagehide").listener({ persisted: true });
  assert.deepEqual(calls, ["stop", "start", "stop", "start", "stop"]);

  // A restored background/hidden document must remain stopped.
  documentLike.hidden = true;
  windowListeners.get("pageshow").listener({ persisted: true });
  assert.deepEqual(
    calls,
    ["stop", "start", "stop", "start", "stop", "stop"]
  );

  // When restored visible again, polling resumes.
  documentLike.hidden = false;
  windowListeners.get("pageshow").listener({ persisted: true });
  assert.deepEqual(
    calls,
    ["stop", "start", "stop", "start", "stop", "stop", "start"]
  );

  cleanup();

  assert.equal(documentListeners.has("visibilitychange"), false);
  assert.equal(windowListeners.has("pagehide"), false);
  assert.equal(windowListeners.has("pageshow"), false);
  assert.deepEqual(
    calls,
    ["stop", "start", "stop", "start", "stop", "stop", "start", "stop"]
  );
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

test("stats ignores stale responses and stopped in-flight loads", async () => {
  const stat = {
    dataset: {
      stat: "cpu_usage",
      decimals: "0",
      suffix: ""
    },
    textContent: ""
  };
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
    querySelectorAll(selector) {
      return selector === "[data-stat]" ? [stat] : [];
    }
  };

  const pending = [];
  const fetchImpl = () => new Promise((resolve, reject) => {
    pending.push({ resolve, reject });
  });

  const windowLike = {
    clearInterval() {},
    setInterval() { return 1; }
  };

  const languageController = {
    language: "en",
    messages: {
      status_live: "Live",
      status_offline: "Offline",
      last_update: "Last update"
    }
  };

  const response = (cpuUsage) => ({
    ok: true,
    async json() {
      return {
        ...liveStats,
        updated: new Date().toISOString(),
        cpu_usage: cpuUsage
      };
    }
  });

  const stats = createStatsController(languageController, {
    root,
    fetchImpl,
    windowLike
  });

  // Newer successful response must remain authoritative even if an older
  // request completes afterwards.
  const olderSuccess = stats.load();
  const newerSuccess = stats.load();

  assert.equal(pending.length, 2);

  pending[1].resolve(response(22));
  await newerSuccess;

  assert.equal(stat.textContent, "22");
  assert.equal(label.textContent, "Live");

  pending[0].resolve(response(11));
  await olderSuccess;

  assert.equal(stat.textContent, "22");
  assert.equal(label.textContent, "Live");

  // A stale failure must not turn a newer successful render offline.
  const staleFailure = stats.load();
  const authoritativeSuccess = stats.load();

  assert.equal(pending.length, 4);

  pending[3].resolve(response(33));
  await authoritativeSuccess;

  assert.equal(stat.textContent, "33");

  pending[2].resolve({
    ok: false,
    async json() { return {}; }
  });
  await staleFailure;

  assert.equal(stat.textContent, "33");
  assert.equal(label.textContent, "Live");

  // stop() invalidates an already-running request.
  const stoppedLoad = stats.load();

  assert.equal(pending.length, 5);

  stats.stop();

  pending[4].resolve(response(44));
  await stoppedLoad;

  assert.equal(stat.textContent, "33");

  // A later request after invalidation can render normally.
  const resumedLoad = stats.load();

  assert.equal(pending.length, 6);

  pending[5].resolve(response(55));
  await resumedLoad;

  assert.equal(stat.textContent, "55");
  assert.equal(label.textContent, "Live");
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
});

test("page entrypoints keep language state inside their intended routing model", async () => {
  const mainSource = await readFile(resolve(ROOT, "frontend/app.mjs"), "utf8");
  assert.match(mainSource, /initialLanguage: document\.documentElement\.lang/);
  assert.match(mainSource, /languageController\.tryApply\(languageController\.language\)/);
  assert.doesNotMatch(mainSource, /querySelectorAll\("\[data-lang\]"\)/);
  assert.doesNotMatch(mainSource, /languageController\.apply\(/);

  const smartHomeSource = await readFile(resolve(ROOT, "frontend/smarthome.mjs"), "utf8");
  assert.match(smartHomeSource, /languageController\.tryApply\(button\.dataset\.lang\)/);
  assert.doesNotMatch(smartHomeSource, /languageController\.apply\(/);
});

test("skill chips map to meaningful SVG icon families", () => {
  assert.equal(skillIconName("Docker Compose"), "container");
  assert.equal(skillIconName("SSL/TLS"), "shield");
  assert.equal(skillIconName("Prometheus"), "chart");
  assert.equal(skillIconName("Home Assistant"), "home");
  assert.equal(skillIconName("ESP32 / IoT"), "chip");
  assert.equal(skillIconName("Terraform"), "cloud");
  assert.equal(skillIconName("RPi5_main"), "chip");
  assert.equal(skillIconName("hermes-deals"), "database");
  assert.equal(skillIconName("rozkalns-control-center"), "gear");
  assert.equal(skillIconName("dashboard_RPi5"), "chart");
});

test("GitHub projects use a compact vertical icon list", async () => {
  const source = await readFile(resolve(ROOT, "frontend/index.html"), "utf8");
  const section = source.match(/<section id="github-projects">([\s\S]*?)<\/section>/)?.[1] || "";
  const featured = section.match(/<div class=skill-list>([\s\S]*?)<\/div>/)?.[1] || "";
  assert.equal((featured.match(/href=\/\/github\.com\/rozkalnsandris\//g) || []).length, 5);
  assert.equal((section.match(/href=\/\/github\.com\/rozkalnsandris\//g) || []).length, 9);
  assert.equal((section.match(/class="tech-tag has-tech-icon github-row"/g) || []).length, 9);
  assert.match(section, /<details class=project-list><summary class="tech-tag">\+ 4 more projects<\/summary><div class=skill-list>/);
});

test("skill icons initialize before translation network work", async () => {
  const source = await readFile(resolve(ROOT, "frontend/app.mjs"), "utf8");
  const iconInit = source.indexOf("enhanceSkillIcons();");
  const translationAwait = source.indexOf("await languageController.tryApply");
  assert.ok(iconInit >= 0);
  assert.ok(translationAwait >= 0);
  assert.ok(iconInit < translationAwait);
});

test("skill translation preserves an existing SVG enhancement", () => {
  const icon = { kind: "svg" };
  const chip = {
    value: "Networking",
    icon,
    querySelector(selector) { return selector === "svg" ? this.icon : null; },
    get textContent() { return this.value; },
    set textContent(value) { this.value = value; this.icon = null; },
    prepend(node) { this.icon = node; }
  };
  const row = {
    querySelector(selector) {
      return selector === "dt[data-i18n]" ? { dataset: { i18n: "skills_foundations" } } : null;
    },
    querySelectorAll(selector) { return selector === ".skill-chip" ? [chip] : []; }
  };
  const root = {
    querySelectorAll(selector) { return selector === ".skill-row" ? [row] : []; }
  };

  assert.equal(
    applySkillTranslations({ skills_foundations_items: "Netzwerke" }, { root }),
    1
  );
  assert.equal(chip.textContent, "Netzwerke");
  assert.equal(chip.icon, icon);
});

test("skill icon enhancement is idempotent and repaired families use complete paths", () => {
  function render(label) {
    const chip = {
      textContent: label,
      icon: null,
      prepends: 0,
      querySelector(selector) { return selector === "svg" ? this.icon : null; },
      prepend(node) { this.icon = node; this.prepends += 1; }
    };
    const root = {
      querySelectorAll(selector) { return selector === ".skill-chip, #github-projects a" ? [chip] : []; },
      createElementNS(_namespace, tagName) {
        return {
          tagName,
          attributes: {},
          children: [],
          setAttribute(name, value) { this.attributes[name] = String(value); },
          append(child) { this.children.push(child); }
        };
      }
    };
    enhanceSkillIcons(root);
    enhanceSkillIcons(root);
    return { chip, svg: chip.icon };
  }

  const shield = render("SSL/TLS");
  assert.equal(shield.chip.prepends, 1);
  assert.equal(shield.svg.attributes["aria-hidden"], "true");
  assert.deepEqual(
    shield.svg.children.map((path) => path.attributes.d),
    [
      "M12 3 19 6v5c0 4.5-2.8 7.7-7 10C7.8 18.7 5 15.5 5 11V6l7-3Z",
      "M9 12l2 2 4-5"
    ]
  );

  const code = render("Python");
  assert.equal(code.chip.prepends, 1);
  assert.deepEqual(
    code.svg.children.map((path) => path.attributes.d),
    ["M8 9 5 12 8 15", "M16 9 19 12 16 15", "M14 5 10 19"]
  );
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


test("GitHub project overflow exposes direct repository links", async () => {
  const source = await readFile(resolve(ROOT, "frontend/index.html"), "utf8");
  const section = source.match(/<section id="github-projects">([\s\S]*?)<\/section>/)?.[1] || "";
  assert.match(section, /<details class=project-list><summary class="tech-tag">\+ 4 more projects<\/summary><div class=skill-list>/);
  for (const repo of ["home-assistant-config", "balcony-irrigation-esp32", "rozkalns-cv", "ops-workflows"]) {
    assert.ok(section.includes(`href=//github.com/rozkalnsandris/${repo}>${repo}</a>`), repo);
  }
});
