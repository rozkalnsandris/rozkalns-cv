import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { createChatController, renderChatPrivacyText } from "../frontend/features/chat.mjs";

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
  assert.equal(
    renderChatPrivacyText(copy, 9),
    copy.chat_privacy_retained.replace("{days}", "9"),
    `${language} runtime retention mismatch`
  );
  for (const invalid of [undefined, "7", -1, 1.5, Number.NaN]) {
    assert.equal(renderChatPrivacyText(copy, invalid), copy.chat_privacy, `${language} accepted invalid retention`);
  }
}

function chatHarness(languageMessages) {
  const observers = [];
  class FakeMutationObserver {
    constructor(callback) { this.callback = callback; observers.push(this); }
    observe() {}
  }
  const form = { addEventListener() {}, setAttribute() {} };
  const privacy = { textContent: "" };
  const root = {
    documentElement: { lang: "en" },
    querySelector(selector) {
      return {
        "#chatForm": form,
        "#chatInput": { value: "", focus() {} },
        "#chatSend": { disabled: false },
        "#chatLog": { append() {}, scrollTop: 0, scrollHeight: 0 },
        "#chatStatus": { textContent: "", after() {} },
        "#chatPrivacy": privacy
      }[selector] || null;
    },
    createElement() { return { className: "", textContent: "", setAttribute() {}, remove() {} }; }
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
  let fetches = 0;
  const controller = createChatController(harness.languageController, {
    root: harness.root,
    windowLike: harness.windowLike,
    fetchImpl: async (url, options = {}) => {
      assert.equal(url, "/api/chat-config");
      assert.equal(options.cache, "no-store");
      fetches += 1;
      return { ok: true, async json() { return { retention_days: 0 }; } };
    }
  });
  assert.equal(harness.privacy.textContent, messages.en.chat_privacy);
  assert.equal(await controller.privacyReady, 0);
  assert.equal(harness.privacy.textContent, messages.en.chat_privacy_zero);
  harness.languageController.messages = messages.de;
  harness.root.documentElement.lang = "de";
  harness.observers[0].callback();
  assert.equal(harness.privacy.textContent, messages.de.chat_privacy_zero);
  assert.equal(fetches, 1, "language rerender refetched runtime policy");
}

{
  const harness = chatHarness(messages.lv);
  const controller = createChatController(harness.languageController, {
    root: harness.root,
    windowLike: harness.windowLike,
    fetchImpl: async () => { throw new TypeError("synthetic config failure"); }
  });
  assert.equal(await controller.privacyReady, null);
  assert.equal(harness.privacy.textContent, messages.lv.chat_privacy);
}

console.log("CHAT_PRIVACY_RUNTIME_CONTRACT=PASS");
