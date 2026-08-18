import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { createChatController } from "../frontend/features/chat.mjs";

const rootDir = resolve(import.meta.dirname, "..");
const messages = Object.fromEntries(await Promise.all(
  ["en", "de", "lv"].map(async (language) => [
    language,
    JSON.parse(await readFile(resolve(rootDir, "content", "translations", `${language}.json`), "utf8"))
  ])
));
const source = await readFile(resolve(rootDir, "frontend", "index.html"), "utf8");
assert.match(source, /id="chatPrivacy"[^>]*data-i18n="chat_privacy"/);
for (const [language, copy] of Object.entries(messages)) {
  assert.doesNotMatch(copy.chat_privacy, /\b7\b/, `${language} fallback hard-codes the old duration`);
  assert.ok(copy.chat_privacy_zero, `${language} zero-retention copy missing`);
  assert.match(copy.chat_privacy_retained, /\{days\}/, `${language} runtime placeholder missing`);
  assert.equal("chat_privacy_one" in copy, false, `${language} retains redundant singular copy`);
}

function harness(languageMessages, privacyText) {
  const observers = [];
  class FakeMutationObserver {
    constructor(callback) { this.callback = callback; observers.push(this); }
    observe() {}
  }
  const privacy = { textContent: privacyText };
  const elements = {
    "#chatForm": { addEventListener() {}, setAttribute() {} },
    "#chatInput": { value: "", focus() {} },
    "#chatSend": { disabled: false },
    "#chatLog": { append() {}, scrollTop: 0, scrollHeight: 0 },
    "#chatStatus": { textContent: "", after() {} },
    "#chatPrivacy": privacy
  };
  return {
    observers,
    privacy,
    root: {
      documentElement: { lang: "en" },
      querySelector(selector) { return elements[selector] || null; },
      createElement() { return { className: "", textContent: "", setAttribute() {}, remove() {} }; }
    },
    windowLike: { MutationObserver: FakeMutationObserver },
    languageController: { messages: languageMessages }
  };
}

async function settle(predicate) {
  for (let attempt = 0; attempt < 20 && !predicate(); attempt += 1) await Promise.resolve();
}

for (const [days, expectedKey] of [[0, "chat_privacy_zero"], [9, "chat_privacy_retained"]]) {
  const h = harness(messages.en, messages.en.chat_privacy);
  let fetches = 0;
  createChatController(h.languageController, {
    root: h.root,
    windowLike: h.windowLike,
    fetchImpl: async (url, options = {}) => {
      assert.equal(url, "/api/chat-config");
      assert.equal(options.cache, "no-store");
      fetches += 1;
      return { ok: true, async json() { return { retention_days: days }; } };
    }
  });
  const expected = messages.en[expectedKey].replace("{days}", String(days));
  await settle(() => h.privacy.textContent === expected);
  assert.equal(h.privacy.textContent, expected);
  assert.equal(fetches, 1);
  h.languageController.messages = messages.de;
  h.root.documentElement.lang = "de";
  h.observers[0].callback();
  assert.equal(h.privacy.textContent, messages.de[expectedKey].replace("{days}", String(days)));
  assert.equal(fetches, 1, "language rerender refetched runtime policy");
}

for (const mode of ["failure", "invalid"]) {
  const h = harness(messages.lv, messages.lv.chat_privacy);
  createChatController(h.languageController, {
    root: h.root,
    windowLike: h.windowLike,
    fetchImpl: mode === "failure"
      ? async () => { throw new TypeError("synthetic config failure"); }
      : async () => ({ ok: true, async json() { return { retention_days: "7" }; } })
  });
  await settle(() => false);
  assert.equal(h.privacy.textContent, messages.lv.chat_privacy);
}

console.log("CHAT_PRIVACY_RUNTIME_CONTRACT=PASS");
