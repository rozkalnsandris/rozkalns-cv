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
      if (chatMode === "success") {
        return new Promise((resolveResponse) => {
          resolveChat = resolveResponse;
        });
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
