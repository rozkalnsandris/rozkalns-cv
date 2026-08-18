import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import {
  createChatController,
  normalizeChatRetentionDays,
  renderChatPrivacyText
} from "../frontend/features/chat.mjs";

const rootDir = resolve(import.meta.dirname, "..");
const messages = Object.fromEntries(await Promise.all(
  ["en", "de", "lv"].map(async (language) => [
    language,
    JSON.parse(await readFile(resolve(rootDir, "content", "translations", `${language}.json`), "utf8"))
  ])
));

for (const [language, copy] of Object.entries(messages)) {
  assert.equal(renderChatPrivacyText(copy, null), copy.chat_privacy, `${language} fallback mismatch`);
  assert.doesNotMatch(copy.chat_privacy, /\b7\b/, `${language} fallback hard-codes the old retention duration`);
  assert.equal(renderChatPrivacyText(copy, 0), copy.chat_privacy_zero, `${language} zero-retention mismatch`);
  assert.equal(renderChatPrivacyText(copy, 1), copy.chat_privacy_one, `${language} singular retention mismatch`);
  const retained = renderChatPrivacyText(copy, 9);
  assert.equal(retained, copy.chat_privacy_retained.replaceAll("{days}", "9"), `${language} runtime retention mismatch`);
  assert.doesNotMatch(retained, /\{days\}/, `${language} runtime placeholder leaked`);
}

for (const value of [null, undefined, "7", -1, 1.5, Number.NaN]) {
  assert.equal(normalizeChatRetentionDays(value), null, `invalid retention accepted: ${String(value)}`);
}
assert.equal(normalizeChatRetentionDays(0), 0);
assert.equal(normalizeChatRetentionDays(14), 14);

function chatHarness(languageMessages) {
  const observers = [];
  class FakeMutationObserver {
    constructor(callback) {
      this.callback = callback;
      observers.push(this);
    }
    observe() {}
  }
  const form = { addEventListener() {}, setAttribute() {} };
  const input = { value: "", focus() {} };
  const send = { disabled: false };
  const log = { append() {}, scrollTop: 0, scrollHeight: 0 };
  const status = { textContent: "", after() {} };
  const privacy = { textContent: "" };
  const root = {
    documentElement: { lang: "en" },
    querySelector(selector) {
      if (selector === "#chatForm") return form;
      if (selector === "#chatInput") return input;
      if (selector === "#chatSend") return send;
      if (selector === "#chatLog") return log;
      if (selector === "#chatStatus") return status;
      if (selector === "#chatPrivacy") return privacy;
      return null;
    },
    createElement() {
      return { className: "", textContent: "", setAttribute() {}, remove() {} };
    }
  };
  return {
    observers,
    privacy,
    root,
    windowLike: { MutationObserver: FakeMutationObserver },
    languageController: { messages: languageMessages }
  };
}

{
  const harness = chatHarness(messages.en);
  let configFetches = 0;
  const fetchImpl = async (url, options = {}) => {
    assert.equal(url, "/api/chat-config");
    assert.equal(options.cache, "no-store");
    configFetches += 1;
    return { ok: true, async json() { return { retention_days: 0 }; } };
  };
  const controller = createChatController(harness.languageController, {
    root: harness.root,
    windowLike: harness.windowLike,
    fetchImpl
  });
  assert.ok(controller);
  assert.equal(harness.privacy.textContent, messages.en.chat_privacy);
  assert.equal(await controller.privacyReady, 0);
  assert.equal(harness.privacy.textContent, messages.en.chat_privacy_zero);
  assert.equal(configFetches, 1);
  assert.equal(harness.observers.length, 1);

  harness.languageController.messages = messages.de;
  harness.root.documentElement.lang = "de";
  harness.observers[0].callback();
  assert.equal(harness.privacy.textContent, messages.de.chat_privacy_zero);
  assert.equal(configFetches, 1, "language rerender refetched runtime policy");
}

{
  const harness = chatHarness(messages.lv);
  const controller = createChatController(harness.languageController, {
    root: harness.root,
    windowLike: harness.windowLike,
    fetchImpl: async () => { throw new TypeError("synthetic config failure"); }
  });
  assert.ok(controller);
  assert.equal(await controller.privacyReady, null);
  assert.equal(harness.privacy.textContent, messages.lv.chat_privacy);
}

console.log("CHAT_PRIVACY_RUNTIME_CONTRACT=PASS");
