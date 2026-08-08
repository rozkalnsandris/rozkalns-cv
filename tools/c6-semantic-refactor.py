from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly one anchor, found {count}: {old[:80]!r}")
    write(path, text.replace(old, new, 1))


def replace_count(path: str, old: str, new: str, expected: int) -> None:
    text = read(path)
    count = text.count(old)
    if count != expected:
        raise SystemExit(f"{path}: expected {expected} anchors, found {count}: {old[:80]!r}")
    write(path, text.replace(old, new))


language_old = '''      <div class="language-switcher" aria-label="Language">
        <button type="button" data-lang="en" aria-pressed="true">EN</button>
        <button type="button" data-lang="de" aria-pressed="false">DE</button>
        <button type="button" data-lang="lv" aria-pressed="false">LV</button>
      </div>'''
language_new = '''      <div class="language-switcher" role="group" aria-label="Language">
        <button type="button" data-lang="en" aria-pressed="true" aria-label="English" lang="en">EN</button>
        <button type="button" data-lang="de" aria-pressed="false" aria-label="Deutsch" lang="de">DE</button>
        <button type="button" data-lang="lv" aria-pressed="false" aria-label="Latviešu" lang="lv">LV</button>
      </div>'''
replace_once("frontend/index.html", language_old, language_new)
replace_once("frontend/smarthome.html", language_old.replace("      ", "      ", 1), language_new.replace("      ", "      ", 1))

replace_once(
    "frontend/index.html",
    '<button id="contactReveal" class="contact-reveal" type="button">',
    '<button id="contactReveal" class="contact-reveal" type="button" aria-controls="turnstileMount" aria-expanded="false">',
)
replace_once(
    "frontend/index.html",
    '''  <div id="chatBackdrop" class="dialog-backdrop" hidden>
    <section id="chatDialog" class="chat-dialog" role="dialog" aria-modal="true" aria-labelledby="chatTitle" aria-describedby="chatPrivacy">''',
    '''  <dialog id="chatDialog" class="chat-dialog" aria-labelledby="chatTitle">''',
)
replace_once(
    "frontend/index.html",
    'autocomplete="off" data-i18n-placeholder="chat_input"',
    'autocomplete="off" autofocus data-i18n-placeholder="chat_input"',
)
replace_once(
    "frontend/index.html",
    '''      <form id="chatForm" class="chat-form" aria-busy="false"><label class="skip-link" for="chatInput" data-i18n="chat_input">Ask about Andris's experience</label><input id="chatInput" name="message" type="text" maxlength="500" autocomplete="off" autofocus data-i18n-placeholder="chat_input" placeholder="Ask about Andris's experience"><button id="chatSend" class="button" type="submit" data-i18n="chat_send">Send</button></form>
    </section>
  </div>''',
    '''      <form id="chatForm" class="chat-form" aria-busy="false"><label class="skip-link" for="chatInput" data-i18n="chat_input">Ask about Andris's experience</label><input id="chatInput" name="message" type="text" maxlength="500" autocomplete="off" autofocus data-i18n-placeholder="chat_input" placeholder="Ask about Andris's experience"><button id="chatSend" class="button" type="submit" data-i18n="chat_send">Send</button></form>
  </dialog>''',
)

chat_path = "frontend/features/chat.mjs"
chat = read(chat_path)
start = chat.index("function focusableElements")
end_marker = "\nfunction appendMessage"
end = chat.index(end_marker, start)
controller = '''export function createDialogController({ root = globalThis.document } = {}) {
  const launcher = root.querySelector("#chatLauncher");
  const dialog = root.querySelector("#chatDialog");
  const input = root.querySelector("#chatInput");
  const close = root.querySelector("#chatClose");
  if (!launcher || !dialog || !input || !close) return null;
  if (typeof dialog.showModal !== "function" || typeof dialog.close !== "function") return null;
  let returnFocus = launcher;

  function restoreFocus() {
    root.body.classList.remove("dialog-open");
    launcher.hidden = false;
    returnFocus?.focus?.();
  }

  function open() {
    if (dialog.open) return;
    returnFocus = root.activeElement?.focus ? root.activeElement : launcher;
    launcher.hidden = true;
    root.body.classList.add("dialog-open");
    dialog.showModal();
    input.focus();
  }

  function dismiss() {
    if (dialog.open) dialog.close();
  }

  function lightDismiss(event) {
    if (event.target !== dialog) return;
    const bounds = dialog.getBoundingClientRect();
    const outside =
      event.clientX < bounds.left ||
      event.clientX > bounds.right ||
      event.clientY < bounds.top ||
      event.clientY > bounds.bottom;
    if (outside) dismiss();
  }

  launcher.addEventListener("click", open);
  close.addEventListener("click", dismiss);
  dialog.addEventListener("close", restoreFocus);
  dialog.addEventListener("click", lightDismiss);
  return { open, dismiss };
}
'''
write(chat_path, chat[:start] + controller + chat[end:])

contact_path = "frontend/features/contact.mjs"
contact = read(contact_path)
mount_anchor = '''  const mount = root.querySelector("#turnstileMount");
  if (!button || !mount) return null;
'''
if contact.count(mount_anchor) != 1:
    raise SystemExit("contact controller mount anchor drift")
contact = contact.replace(mount_anchor, mount_anchor + "  let started = false;\n", 1)
contact = contact.replace(
    '''    button.hidden = true;
    mount.hidden = true;
    setStatus(root, message("contact_success"), "success");''',
    '''    button.hidden = true;
    mount.hidden = true;
    button.setAttribute("aria-expanded", "false");
    setStatus(root, message("contact_success"), "success");''',
    1,
)
start = contact.index("  async function start() {")
end = contact.index("\n\n  refreshCopy();", start)
new_start = '''  async function start() {
    if (started) return;
    started = true;
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
      button.setAttribute("aria-expanded", "true");
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
      started = false;
      button.setAttribute("aria-expanded", "false");
      setStatus(root, message("contact_unavailable"), "error");
      delete button.dataset.locked;
      refreshCopy();
    }
  }'''
contact = contact[:start] + new_start + contact[end:]
if "button.disabled = true" in contact or "button.disabled = false" in contact:
    raise SystemExit("contact trigger still disables keyboard focus")
write(contact_path, contact)

replace_once(
    "frontend/styles/features/chat.css",
    '.dialog-backdrop { position: fixed; inset: 0; z-index: 50; display: grid; place-items: end; padding: 22px; background: rgba(0,0,0,.48); }\n.chat-dialog { width: min(380px,calc(100vw - 32px)); height: min(560px,calc(100vh - 44px)); display: flex; flex-direction: column; overflow: hidden; border: 1px solid var(--border); border-radius: 14px; background: var(--bg); box-shadow: 0 18px 50px rgba(0,0,0,.5); }',
    '.chat-dialog { position: fixed; inset: auto 22px 22px auto; width: min(380px,calc(100vw - 32px)); height: min(560px,calc(100vh - 44px)); max-width: none; max-height: none; margin: 0; padding: 0; overflow: hidden; border: 1px solid var(--border); border-radius: 14px; background: var(--bg); color: var(--text); box-shadow: 0 18px 50px rgba(0,0,0,.5); }\n.chat-dialog[open] { display: flex; flex-direction: column; }\n.chat-dialog::backdrop { background: rgba(0,0,0,.48); }',
)
replace_once(
    "frontend/styles/responsive.css",
    '  .dialog-backdrop { padding: 0; }\n  .chat-dialog { width: 100%; height: 100%; border: 0; border-radius: 0; }',
    '  .chat-dialog { inset: 0; width: 100%; height: 100%; max-width: none; max-height: none; border: 0; border-radius: 0; }',
)
replace_once(
    "frontend/styles/features/smarthome.css",
    ".demo-device h2 { margin: 0 0 9px; color: var(--text); font-size: 15px; }",
    ".demo-device h3 { margin: 0 0 9px; color: var(--text); font-size: 15px; }",
)
replace_count("frontend/smarthome.html", '<article class="demo-device card"><h2', '<article class="demo-device card"><h3', 8)
replace_count("frontend/smarthome.html", '</h2><div class="demo-value">', '</h3><div class="demo-value">', 8)

frontend_test = read("tests/frontend.test.mjs")
insert_anchor = '''test("skill chips map to meaningful SVG icon families", () => {'''
if frontend_test.count(insert_anchor) != 1:
    raise SystemExit("frontend test insertion anchor drift")
new_tests = '''test("native dialog owns modal focus containment and Escape semantics", async () => {
  const source = await readFile(resolve(ROOT, "frontend/features/chat.mjs"), "utf8");
  assert.match(source, /dialog\.showModal\(\)/);
  assert.match(source, /dialog\.close\(\)/);
  assert.match(source, /dialog\.addEventListener\("close", restoreFocus\)/);
  assert.doesNotMatch(source, /focusableElements|shell\.inert|event\.key === "Escape"|event\.key !== "Tab"/);
});

test("contact verification keeps its keyboard trigger operable while loading", async () => {
  const source = await readFile(resolve(ROOT, "frontend/features/contact.mjs"), "utf8");
  assert.match(source, /if \(started\) return;/);
  assert.match(source, /button\.setAttribute\("aria-expanded", "true"\)/);
  assert.match(source, /button\.setAttribute\("aria-expanded", "false"\)/);
  assert.doesNotMatch(source, /button\.disabled\s*=\s*true/);
});

'''
frontend_test = frontend_test.replace(insert_anchor, new_tests + insert_anchor, 1)
write("tests/frontend.test.mjs", frontend_test)

semantics_path = "tests/test_html_semantics.py"
semantics = read(semantics_path)
start = semantics.index("    def test_cv_dialog_has_complete_modal_contract")
end = semantics.index("\n    def test_fingerprinted_assets_are_manifest_owned", start)
new_semantics = '''    def test_cv_dialog_has_complete_modal_contract(self) -> None:
        parsed = parse(HTML_ROOT / "index.html")
        by_id = {
            row.attrs["id"]: row
            for row in parsed.elements
            if row.attrs.get("id")
        }
        dialog = by_id["chatDialog"]
        self.assertEqual(dialog.tag, "dialog")
        self.assertNotIn("role", dialog.attrs)
        self.assertNotIn("aria-modal", dialog.attrs)
        self.assertNotIn("aria-describedby", dialog.attrs)
        self.assertIn(dialog.attrs.get("aria-labelledby"), by_id)
        self.assertIn("autofocus", by_id["chatInput"].attrs)
        self.assertEqual(by_id["chatStatus"].attrs.get("role"), "status")
        self.assertEqual(by_id["chatLog"].attrs.get("role"), "log")
        self.assertEqual(by_id["chatLog"].attrs.get("aria-live"), "polite")
        self.assertEqual(by_id["chatLog"].attrs.get("aria-relevant"), "additions")
        self.assertEqual(by_id["contactReveal"].attrs.get("aria-controls"), "turnstileMount")
        self.assertEqual(by_id["contactReveal"].attrs.get("aria-expanded"), "false")

        switchers = [
            row for row in parsed.elements
            if row.attrs.get("class") == "language-switcher"
        ]
        self.assertEqual(len(switchers), 1)
        self.assertEqual(switchers[0].attrs.get("role"), "group")
        self.assertEqual(switchers[0].attrs.get("aria-label"), "Language")
        language_buttons = {
            row.attrs.get("data-lang"): row
            for row in parsed.elements
            if row.tag == "button" and row.attrs.get("data-lang")
        }
        self.assertEqual(set(language_buttons), {"en", "de", "lv"})
        self.assertEqual(language_buttons["en"].attrs.get("aria-label"), "English")
        self.assertEqual(language_buttons["de"].attrs.get("aria-label"), "Deutsch")
        self.assertEqual(language_buttons["lv"].attrs.get("aria-label"), "Latviešu")
        self.assertEqual(language_buttons["en"].attrs.get("aria-pressed"), "true")
        self.assertEqual(language_buttons["de"].attrs.get("aria-pressed"), "false")
        self.assertEqual(language_buttons["lv"].attrs.get("aria-pressed"), "false")

        skip_links = [
            row
            for row in parsed.elements
            if row.tag == "a" and row.attrs.get("href") == "#main"
        ]
        self.assertEqual(len(skip_links), 1)

    def test_smarthome_heading_hierarchy_and_language_group(self) -> None:
        parsed = parse(HTML_ROOT / "smarthome.html")
        headings = [row for row in parsed.elements if row.tag in {"h1", "h2", "h3"}]
        self.assertEqual(sum(row.tag == "h1" for row in headings), 1)
        self.assertEqual(sum(row.tag == "h2" for row in headings), 2)
        self.assertEqual(sum(row.tag == "h3" for row in headings), 8)
        switchers = [
            row for row in parsed.elements
            if row.attrs.get("class") == "language-switcher"
        ]
        self.assertEqual(len(switchers), 1)
        self.assertEqual(switchers[0].attrs.get("role"), "group")
        self.assertEqual(switchers[0].attrs.get("aria-label"), "Language")
'''
semantics = semantics[:start] + new_semantics + semantics[end:]
write(semantics_path, semantics)

browser_path = "tests/browser-smoke.mjs"
browser = read(browser_path)
replace_old = '''    const initialContract = await cdp.evaluate(`(() => ({
      role: document.querySelector('[data-i18n="role"]')?.textContent,
      pdf: document.querySelector('#pdfLink')?.getAttribute('href'),
      dialogModal: document.querySelector('#chatDialog')?.getAttribute('aria-modal'),
      privacy: document.querySelector('[data-i18n="chat_privacy"]')?.textContent
    }))()`);
    assert.equal(initialContract.role, "Junior DevOps & Linux Engineer");
    assert.equal(initialContract.pdf, "/cv.pdf");
    assert.equal(initialContract.dialogModal, "true");
    assert.match(initialContract.privacy, /raw IP addresses are not stored/i);'''
replace_new = '''    const initialContract = await cdp.evaluate(`(() => ({
      role: document.querySelector('[data-i18n="role"]')?.textContent,
      pdf: document.querySelector('#pdfLink')?.getAttribute('href'),
      dialogTag: document.querySelector('#chatDialog')?.tagName,
      dialogLabelledBy: document.querySelector('#chatDialog')?.getAttribute('aria-labelledby'),
      languageGroupRole: document.querySelector('.language-switcher')?.getAttribute('role'),
      languageButtons: [...document.querySelectorAll('[data-lang]')].map((button) => ({
        language: button.dataset.lang,
        pressed: button.getAttribute('aria-pressed'),
        label: button.getAttribute('aria-label')
      })),
      privacy: document.querySelector('[data-i18n="chat_privacy"]')?.textContent
    }))()`);
    assert.equal(initialContract.role, "Junior DevOps & Linux Engineer");
    assert.equal(initialContract.pdf, "/cv.pdf");
    assert.equal(initialContract.dialogTag, "DIALOG");
    assert.equal(initialContract.dialogLabelledBy, "chatTitle");
    assert.equal(initialContract.languageGroupRole, "group");
    assert.deepEqual(initialContract.languageButtons, [
      { language: "en", pressed: "true", label: "English" },
      { language: "de", pressed: "false", label: "Deutsch" },
      { language: "lv", pressed: "false", label: "Latviešu" }
    ]);
    assert.match(initialContract.privacy, /raw IP addresses are not stored/i);'''
if browser.count(replace_old) != 1:
    raise SystemExit("browser initial contract anchor drift")
browser = browser.replace(replace_old, replace_new, 1)

lv_assert = '''    assert.equal(
      await cdp.evaluate(`document.querySelector('[data-i18n="role"]').textContent`),
      "Junior DevOps un Linux inženieris"
    );'''
if browser.count(lv_assert) != 1:
    raise SystemExit("browser LV assertion anchor drift")
browser = browser.replace(
    lv_assert,
    lv_assert + '''
    assert.deepEqual(
      await cdp.evaluate(`[...document.querySelectorAll('[data-lang]')].map((button) => button.getAttribute('aria-pressed'))`),
      ["false", "false", "true"]
    );''',
    1,
)

replace_once_text = '''      `document.querySelector('#chatBackdrop').hidden === false && document.activeElement?.id === "chatInput" && document.querySelector('#pageShell').inert === true`,'''
if browser.count(replace_once_text) != 1:
    raise SystemExit("browser dialog open anchor drift")
browser = browser.replace(
    replace_once_text,
    '''      `document.querySelector('#chatDialog')?.open === true && document.activeElement?.id === "chatInput" && document.querySelector('#chatLauncher')?.hidden === true`,''',
    1,
)
close_focus = '''    await cdp.evaluate(`document.querySelector('#chatClose').focus()`);'''
if browser.count(close_focus) != 1:
    raise SystemExit("browser close focus anchor drift")
browser = browser.replace(
    close_focus,
    '''    await cdp.evaluate(`document.querySelector('#pdfLink').focus()`);
    assert.notEqual(await cdp.evaluate(`document.activeElement?.id`), "pdfLink");
    await cdp.evaluate(`document.querySelector('#chatClose').focus()`);''',
    1,
)
replace_close = '''      `document.querySelector('#chatBackdrop').hidden === true && document.activeElement?.id === "chatLauncher" && document.querySelector('#pageShell').inert === false`,'''
if browser.count(replace_close) != 1:
    raise SystemExit("browser dialog close anchor drift")
browser = browser.replace(
    replace_close,
    '''      `document.querySelector('#chatDialog')?.open === false && document.activeElement?.id === "chatLauncher" && document.querySelector('#chatLauncher')?.hidden === false`,''',
    1,
)
first_submit = '''    await submit("First question", "Atbilde pabeigta.");'''
if browser.count(first_submit) != 1:
    raise SystemExit("browser first submit anchor drift")
browser = browser.replace(
    first_submit,
    first_submit + '''
    const chatAnnouncementContract = await cdp.evaluate(`(() => ({
      logRole: document.querySelector('#chatLog')?.getAttribute('role'),
      logLive: document.querySelector('#chatLog')?.getAttribute('aria-live'),
      logRelevant: document.querySelector('#chatLog')?.getAttribute('aria-relevant'),
      statusRole: document.querySelector('#chatStatus')?.getAttribute('role'),
      streamedAnswerLive: [...document.querySelectorAll('#chatLog .message.bot')].at(-1)?.getAttribute('aria-live')
    }))()`);
    assert.deepEqual(chatAnnouncementContract, {
      logRole: "log",
      logLive: "polite",
      logRelevant: "additions",
      statusRole: "status",
      streamedAnswerLive: "off"
    });''',
    1,
)
write(browser_path, browser)

(ROOT / "docs/A11Y_C6_AUDIT.md").write_text(
    """# Gate C6 semantic interaction and accessibility audit\n\n"
    "Baseline: production-verified C5 `a044e4c612f4952e0d59a8b2b76779137f92d06e`.\n\n"
    "## Native dialog decision\n\n"
    "Current HTML/ARIA guidance was re-checked before implementation. `HTMLDialogElement.showModal()` places the dialog in the top layer and makes the rest of the document inert. Native modal dialogs also provide the platform Escape/close-request behavior and browser-managed focus containment. W3C WCAG technique H102 recommends the native `dialog` element to reduce custom modal implementation effort, with focus returning to the invoking control.\n\n"
    "C6 therefore replaces the custom `section[role=dialog]` + backdrop + manual Tab trap + manual `inert`/Escape handling with a native `<dialog>` opened by `showModal()`. The explicit close button, return-focus policy, scroll lock and click-outside dismissal remain. The structured chat transcript/privacy/form content is no longer forced through `aria-describedby`; the visible `chatTitle` remains the dialog accessible name.\n\n"
    "## Other semantic hardening\n\n"
    "- language toggle buttons are exposed as one named `role=group`, retain `aria-pressed`, and use full language accessible names (`English`, `Deutsch`, `Latviešu`);\n"
    "- contact verification exposes `aria-controls`/`aria-expanded` and no longer disables the focused trigger while the Turnstile challenge loads; repeated activation is guarded internally;\n"
    "- the chat transcript keeps `role=log` with additions-only live relevance while the streaming answer item explicitly has `aria-live=off`; `role=status` announces preparation/completion rather than every streamed chunk;\n"
    "- Smart Home device-card headings move from `h2` to `h3`, preserving the section `h2` hierarchy and visual styling.\n\n"
    "## Preserved contracts\n\n"
    "C5 lazy chat/contact imports, hidden-tab stats lifecycle, Turnstile interaction-only loading, contact secrecy, `cvlang`, PDF switching, chat API/history/streaming semantics, strict CSP, deterministic Vite output and production deployment ownership are unchanged. No RPi5 pull-request execution or Cloudflare Tunnel lifecycle change is part of C6.\n",
    encoding="utf-8",
)

print("C6_SEMANTIC_REFACTOR=APPLIED")
