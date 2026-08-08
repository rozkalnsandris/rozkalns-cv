from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_exact(path: str, old: str, new: str, *, count: int = 1) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"{path}: expected {count} occurrences, found {actual}: {old[:80]!r}")
    target.write_text(text.replace(old, new), encoding="utf-8")


language_old = '''      <div class="language-switcher" aria-label="Language">
        <button type="button" data-lang="en" aria-pressed="true">EN</button>
        <button type="button" data-lang="de" aria-pressed="false">DE</button>
        <button type="button" data-lang="lv" aria-pressed="false">LV</button>
      </div>'''
language_new = '''      <div class="language-switcher" role="group" aria-label="Language">
        <button type="button" data-lang="en" aria-label="English" aria-pressed="true">EN</button>
        <button type="button" data-lang="de" aria-label="Deutsch" aria-pressed="false">DE</button>
        <button type="button" data-lang="lv" aria-label="Latviešu" aria-pressed="false">LV</button>
      </div>'''
replace_exact("frontend/index.html", language_old, language_new)
replace_exact("frontend/smarthome.html", language_old, language_new)

replace_exact(
    "frontend/smarthome.html",
    '<article class="demo-device card"><h2',
    '<article class="demo-device card"><h3',
    count=8,
)
replace_exact(
    "frontend/smarthome.html",
    '</h2><div class="demo-value">',
    '</h3><div class="demo-value">',
    count=8,
)
replace_exact(
    "frontend/styles/features/smarthome.css",
    ".demo-device h2 { margin: 0 0 9px; color: var(--text); font-size: 15px; }",
    ".demo-device h3 { margin: 0 0 9px; color: var(--text); font-size: 15px; }",
)

replace_exact(
    "frontend/features/contact.mjs",
    '''  element.replaceWith(link);
  link.dataset.revealed = "true";
}''',
    '''  element.replaceWith(link);
  link.dataset.revealed = "true";
  return link;
}''',
)
replace_exact(
    "frontend/features/contact.mjs",
    '''    const email = root.querySelector("#contactEmail");
    const phone = root.querySelector("#contactPhone");
    if (email) revealLink(root, email, payload.email, `mailto:${payload.email}`);
    if (phone) revealLink(root, phone, payload.phone, `tel:${payload.phone_uri}`);
    button.hidden = true;
    mount.hidden = true;
    setStatus(root, message("contact_success"), "success");
    return true;''',
    '''    const email = root.querySelector("#contactEmail");
    const phone = root.querySelector("#contactPhone");
    const emailLink = email ? revealLink(root, email, payload.email, `mailto:${payload.email}`) : null;
    const phoneLink = phone ? revealLink(root, phone, payload.phone, `tel:${payload.phone_uri}`) : null;
    button.hidden = true;
    mount.hidden = true;
    setStatus(root, message("contact_success"), "success");
    windowLike.setTimeout(() => (emailLink || phoneLink)?.focus(), 0);
    return true;''',
)

browser = "tests/browser-smoke.mjs"
replace_exact(
    browser,
    '''      if (url.pathname === "/api/chat" && request.method === "POST") {''',
    '''      if (url.pathname === "/api/contact-config" && request.method === "GET") {
        response.writeHead(200, {
          "Content-Type": "application/json; charset=utf-8",
          "Cache-Control": "no-store"
        });
        response.end(JSON.stringify({ configured: true, sitekey: "fixture-site-key" }));
        return;
      }

      if (url.pathname === "/api/contact-reveal" && request.method === "POST") {
        const body = JSON.parse(await readRequestBody(request));
        state.contactRequests.push(body);
        response.writeHead(200, {
          "Content-Type": "application/json; charset=utf-8",
          "Cache-Control": "no-store"
        });
        response.end(JSON.stringify({
          email: "test@example.invalid",
          phone: "+49 123 4567890",
          phone_uri: "+491234567890"
        }));
        return;
      }

      if (url.pathname === "/api/chat" && request.method === "POST") {''',
)
replace_exact(
    browser,
    '    const virtualKeyCode = key === "Escape" ? 27 : key === "Tab" ? 9 : 0;',
    '    const virtualKeyCode = key === "Escape" ? 27 : key === "Tab" ? 9 : key === "Enter" ? 13 : 0;',
)
replace_exact(
    browser,
    '''    assert.match(initialContract.privacy, /raw IP addresses are not stored/i);
''',
    '''    assert.match(initialContract.privacy, /raw IP addresses are not stored/i);
    const initialLanguageState = await cdp.evaluate(`(() => ({
      groupRole: document.querySelector('.language-switcher')?.getAttribute('role'),
      groupLabel: document.querySelector('.language-switcher')?.getAttribute('aria-label'),
      buttons: [...document.querySelectorAll('.language-switcher [data-lang]')].map((button) => ({
        language: button.dataset.lang,
        label: button.getAttribute('aria-label'),
        pressed: button.getAttribute('aria-pressed')
      })),
      logLive: document.querySelector('#chatLog')?.getAttribute('aria-live'),
      statusRole: document.querySelector('#chatStatus')?.getAttribute('role')
    }))()`);
    assert.equal(initialLanguageState.groupRole, "group");
    assert.equal(initialLanguageState.groupLabel, "Language");
    assert.deepEqual(initialLanguageState.buttons, [
      { language: "en", label: "English", pressed: "true" },
      { language: "de", label: "Deutsch", pressed: "false" },
      { language: "lv", label: "Latviešu", pressed: "false" }
    ]);
    assert.equal(initialLanguageState.logLive, "polite");
    assert.equal(initialLanguageState.statusRole, "status");
''',
)
replace_exact(
    browser,
    '''    assert.equal(
      await cdp.evaluate(`document.querySelector('[data-i18n="role"]').textContent`),
      "Junior DevOps un Linux inženieris"
    );
''',
    '''    assert.equal(
      await cdp.evaluate(`document.querySelector('[data-i18n="role"]').textContent`),
      "Junior DevOps un Linux inženieris"
    );
    assert.deepEqual(
      await cdp.evaluate(`[...document.querySelectorAll('.language-switcher [data-lang]')].map((button) => [button.dataset.lang, button.getAttribute('aria-pressed')])`),
      [["en", "false"], ["de", "false"], ["lv", "true"]]
    );
''',
)
replace_exact(
    browser,
    '''    await cdp.key("Tab", 8);
    assert.equal(await cdp.evaluate(`document.activeElement?.id`), "chatSend");
    await cdp.key("Escape");''',
    '''    await cdp.key("Tab", 8);
    assert.equal(await cdp.evaluate(`document.activeElement?.id`), "chatSend");
    await cdp.key("Tab");
    assert.equal(await cdp.evaluate(`document.activeElement?.id`), "chatClose");
    await cdp.key("Escape");''',
)
replace_exact(
    browser,
    '''    await submit("First question", "Atbilde pabeigta.");
    assert.deepEqual(state.chatRequests[0], {''',
    '''    await submit("First question", "Atbilde pabeigta.");
    const announcementContract = await cdp.evaluate(`(() => ({
      answerLive: document.querySelector('#chatLog .message.bot:last-child')?.getAttribute('aria-live'),
      logLive: document.querySelector('#chatLog')?.getAttribute('aria-live'),
      statusRole: document.querySelector('#chatStatus')?.getAttribute('role'),
      statusLive: document.querySelector('#chatStatus')?.getAttribute('aria-live')
    }))()`);
    assert.equal(announcementContract.answerLive, "off");
    assert.equal(announcementContract.logLive, "polite");
    assert.equal(announcementContract.statusRole, "status");
    assert.equal(announcementContract.statusLive, "polite");
    assert.deepEqual(state.chatRequests[0], {''',
)
replace_exact(
    browser,
    '''    state.statsMode = "stale";
''',
    '''    await cdp.key("Escape");
    await cdp.waitFor(
      `document.querySelector('#chatBackdrop').hidden === true && document.activeElement?.id === "chatLauncher"`,
      5_000,
      "chat focus return before contact verification"
    );
    await cdp.evaluate(`(() => {
      window.turnstile = {
        render(mount, options) {
          const frame = document.createElement('iframe');
          frame.title = 'Synthetic Turnstile';
          frame.tabIndex = 0;
          mount.append(frame);
          setTimeout(() => options.callback('synthetic-turnstile-token'), 0);
          return 'fixture-widget';
        },
        reset() {}
      };
      document.querySelector('#contactReveal').focus();
    })()`);
    await cdp.key("Enter");
    await cdp.waitFor(
      `document.querySelector('#contactReveal')?.hidden === true && document.querySelector('#turnstileMount')?.hidden === true && document.querySelector('#contactVerifyStatus')?.dataset.state === "success" && document.activeElement?.dataset.revealed === "true"`,
      10_000,
      "keyboard contact verification focus transfer"
    );
    assert.deepEqual(state.contactRequests, [{ token: "synthetic-turnstile-token" }]);
    assert.equal(
      await cdp.evaluate(`document.activeElement?.getAttribute('href')`),
      "mailto:test@example.invalid"
    );

    state.statsMode = "stale";
''',
)
replace_exact(
    browser,
    '''    assert(linkState.hrefs.includes("/smarthome.html"), `link-state=${JSON.stringify(linkState)}`);
''',
    '''    assert(linkState.hrefs.includes("/smarthome.html"), `link-state=${JSON.stringify(linkState)}`);

    await cdp.send("Emulation.setDeviceMetricsOverride", {
      width: 390,
      height: 844,
      deviceScaleFactor: 1,
      mobile: true
    });
    await cdp.navigate(`${baseUrl}/smarthome.html`);
    await cdp.waitFor(
      `document.readyState === "complete" && document.querySelector('#demoMain h1')`,
      10_000,
      "Smart Home mobile semantics"
    );
    const smartSemantics = await cdp.evaluate(`(() => ({
      mainCount: document.querySelectorAll('main').length,
      h1Count: document.querySelectorAll('#demoMain h1').length,
      sectionH2Count: document.querySelectorAll('#demoMain > section > .section-heading > h2').length,
      deviceH3Count: document.querySelectorAll('.demo-device h3').length,
      languageRole: document.querySelector('.language-switcher')?.getAttribute('role'),
      languageLabels: [...document.querySelectorAll('.language-switcher [data-lang]')].map((button) => button.getAttribute('aria-label'))
    }))()`);
    assert.equal(smartSemantics.mainCount, 1);
    assert.equal(smartSemantics.h1Count, 1);
    assert.equal(smartSemantics.sectionH2Count, 2);
    assert.equal(smartSemantics.deviceH3Count, 8);
    assert.equal(smartSemantics.languageRole, "group");
    assert.deepEqual(smartSemantics.languageLabels, ["English", "Deutsch", "Latviešu"]);
''',
)
replace_exact(
    browser,
    'const state = { statsMode: "live", chatRequests: [] };',
    'const state = { statsMode: "live", chatRequests: [], contactRequests: [] };',
)

semantic = "tests/test_html_semantics.py"
replace_exact(
    semantic,
    '''    def test_fingerprinted_assets_are_manifest_owned(self) -> None:
''',
    '''    def test_language_switchers_are_named_toggle_groups(self) -> None:
        expected_labels = {"en": "English", "de": "Deutsch", "lv": "Latviešu"}
        for path in self.pages:
            parsed = parse(path)
            switchers = [
                row
                for row in parsed.elements
                if "language-switcher" in row.attrs.get("class", "").split()
            ]
            self.assertEqual(len(switchers), 1, path.name)
            switcher = switchers[0]
            self.assertEqual(switcher.attrs.get("role"), "group")
            self.assertEqual(switcher.attrs.get("aria-label"), "Language")
            buttons = [row for row in parsed.elements if row.attrs.get("data-lang")]
            self.assertEqual({row.attrs.get("data-lang") for row in buttons}, set(expected_labels))
            self.assertEqual(
                {row.attrs.get("data-lang"): row.attrs.get("aria-label") for row in buttons},
                expected_labels,
            )
            pressed = [row for row in buttons if row.attrs.get("aria-pressed") == "true"]
            self.assertEqual(len(pressed), 1)
            self.assertTrue(all(row.attrs.get("aria-pressed") in {"true", "false"} for row in buttons))

    def test_smarthome_heading_hierarchy(self) -> None:
        parsed = parse(HTML_ROOT / "smarthome.html")
        h1 = [row for row in parsed.elements if row.tag == "h1"]
        h2 = [row for row in parsed.elements if row.tag == "h2"]
        h3 = [row for row in parsed.elements if row.tag == "h3"]
        self.assertEqual(len(h1), 1)
        self.assertEqual([row.accessible_text for row in h2], ["Climate", "Devices"])
        self.assertEqual(len(h3), 8)

    def test_fingerprinted_assets_are_manifest_owned(self) -> None:
''',
)
replace_exact(
    semantic,
    '''        self.assertEqual(by_id["chatLog"].attrs.get("aria-live"), "polite")
''',
    '''        self.assertEqual(by_id["chatLog"].attrs.get("aria-live"), "polite")
        self.assertEqual(by_id["chatLog"].attrs.get("aria-relevant"), "additions")
        self.assertEqual(by_id["chatLog"].attrs.get("aria-atomic"), "false")
        self.assertEqual(by_id["chatStatus"].attrs.get("aria-live"), "polite")
''',
)

print("C6_SOURCE_TRANSFORM=PASS")
