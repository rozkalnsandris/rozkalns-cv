from __future__ import annotations

import json
import re
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
        raise SystemExit(f"{path}: expected one match, got {count}: {old[:100]!r}")
    write(path, text.replace(old, new, 1))


# Main document: canonical /en/ identity, reciprocal hreflang, and crawlable language links.
path = "frontend/index.html"
text = read(path)
text = text.replace(
    '<meta property="og:url" content="https://rozkalns.net/">',
    '<meta property="og:url" content="https://rozkalns.net/en/">',
    1,
)
text = text.replace(
    '<link rel="canonical" href="https://rozkalns.net/">',
    '<link rel="canonical" href="https://rozkalns.net/en/">\n'
    '  <link rel="alternate" hreflang="en" href="https://rozkalns.net/en/">\n'
    '  <link rel="alternate" hreflang="de" href="https://rozkalns.net/de/">\n'
    '  <link rel="alternate" hreflang="lv" href="https://rozkalns.net/lv/">\n'
    '  <link rel="alternate" hreflang="x-default" href="https://rozkalns.net/en/">',
    1,
)
profile_pattern = re.compile(r'<script type="application/ld\+json">(.*?)</script>')
match = profile_pattern.search(text)
if not match:
    raise SystemExit("frontend/index.html: JSON-LD missing")
profile = json.loads(match.group(1))
profile["@id"] = "https://rozkalns.net/en/#profile"
profile["url"] = "https://rozkalns.net/en/"
profile["mainEntity"]["url"] = "https://rozkalns.net/en/"
text = text[: match.start(1)] + json.dumps(profile, separators=(",", ":"), ensure_ascii=False) + text[match.end(1) :]
old_switcher = '''      <div class="language-switcher" role="group" data-i18n-label="profile_languages_label" aria-label="Language">
        <button type="button" data-lang="en" aria-label="English" aria-pressed="true">EN</button>
        <button type="button" data-lang="de" aria-label="Deutsch" aria-pressed="false">DE</button>
        <button type="button" data-lang="lv" aria-label="Latviešu" aria-pressed="false">LV</button>
      </div>'''
new_switcher = '''      <nav class="language-switcher" data-i18n-label="profile_languages_label" aria-label="Language">
        <a href="/en/" data-lang="en" aria-label="English" aria-current="page">EN</a>
        <a href="/de/" data-lang="de" aria-label="Deutsch">DE</a>
        <a href="/lv/" data-lang="lv" aria-label="Latviešu">LV</a>
      </nav>'''
if text.count(old_switcher) != 1:
    raise SystemExit("frontend/index.html: language switcher block mismatch")
text = text.replace(old_switcher, new_switcher, 1)
write(path, text)

# Shared styling supports URL links on main CV while preserving buttons on Smart Home.
replace_once(
    "frontend/styles/components.css",
    '.language-switcher button { min-width: 48px; min-height: 48px; padding: 8px 11px; border: 1px solid var(--border); border-radius: 999px; background: var(--surface); color: var(--text-faint); cursor: pointer; font: 700 11px/1 var(--sans); letter-spacing: .05em; box-shadow: var(--shadow-sm); }\n.language-switcher button:hover { color: var(--text); border-color: var(--accent-line); background: var(--accent-soft); }\n.language-switcher button[aria-pressed="true"] { color: #fff; border-color: var(--accent); background: var(--accent); }',
    '.language-switcher button, .language-switcher a { min-width: 48px; min-height: 48px; display: inline-flex; align-items: center; justify-content: center; padding: 8px 11px; border: 1px solid var(--border); border-radius: 999px; background: var(--surface); color: var(--text-faint); cursor: pointer; font: 700 11px/1 var(--sans); letter-spacing: .05em; box-shadow: var(--shadow-sm); text-decoration: none; }\n.language-switcher button:hover, .language-switcher a:hover { color: var(--text); border-color: var(--accent-line); background: var(--accent-soft); text-decoration: none; }\n.language-switcher button[aria-pressed="true"], .language-switcher a[aria-current="page"] { color: #fff; border-color: var(--accent); background: var(--accent); }',
)

# I18n controller can be seeded by a localized document and handles both link and button controls.
replace_once(
    "frontend/core/i18n.mjs",
    '''  root.querySelectorAll("[data-lang]").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.lang === safe));
  });''',
    '''  root.querySelectorAll("[data-lang]").forEach((control) => {
    const selected = control.dataset.lang === safe;
    if (String(control.tagName || "").toUpperCase() === "A") {
      control.removeAttribute("aria-pressed");
      if (selected) control.setAttribute("aria-current", "page");
      else control.removeAttribute("aria-current");
    } else {
      control.removeAttribute("aria-current");
      control.setAttribute("aria-pressed", String(selected));
    }
  });''',
)
replace_once(
    "frontend/core/i18n.mjs",
    '''  navigatorLike = globalThis.navigator,
  fetchImpl = globalThis.fetch,
  pdfs = null,
  onApplied = null
} = {}) {
  let language = preferredLanguage({ storage, navigatorLike });''',
    '''  navigatorLike = globalThis.navigator,
  fetchImpl = globalThis.fetch,
  pdfs = null,
  onApplied = null,
  initialLanguage = null
} = {}) {
  let language = initialLanguage === null
    ? preferredLanguage({ storage, navigatorLike })
    : normalizeLanguage(initialLanguage);''',
)

# Main CV URL owns initial language; language links navigate instead of mutating one URL in place.
replace_once(
    "frontend/app.mjs",
    '''  const languageController = createLanguageController({ pdfs: PDFS, onApplied: updateMainDocumentTitle });
  const preferredApplied = await languageController.tryApply(languageController.language);
  if (!preferredApplied) await languageController.tryApply("en");''',
    '''  const languageController = createLanguageController({
    pdfs: PDFS,
    onApplied: updateMainDocumentTitle,
    initialLanguage: document.documentElement.lang
  });
  await languageController.tryApply(languageController.language);''',
)
replace_once(
    "frontend/app.mjs",
    '''  document.querySelectorAll("[data-lang]").forEach((button) => {
    button.addEventListener("click", () => {
      void languageController.tryApply(button.dataset.lang).then((applied) => {
        if (applied) stats.rerender();
      });
    });
  });

''',
    "",
)

# Build creates localized directories after Vite and removes them before each rebuild.
replace_once(
    "scripts/build-frontend.mjs",
    'import { build } from "vite";\n',
    'import { build } from "vite";\nimport { LOCALIZED_LANGUAGES, renderLocalizedPages } from "./localize-frontend.mjs";\n',
)
replace_once(
    "scripts/build-frontend.mjs",
    '''    rm(resolve(html, "smarthome.html"), { force: true }),
    rm(committedManifest, { force: true })''',
    '''    rm(resolve(html, "smarthome.html"), { force: true }),
    ...LOCALIZED_LANGUAGES.map((language) => rm(resolve(html, language), { recursive: true, force: true })),
    rm(committedManifest, { force: true })''',
)
replace_once(
    "scripts/build-frontend.mjs",
    '''await verifyGeneratedShape();
console.log("FRONTEND_BUILD=PASS");''',
    '''await verifyGeneratedShape();
await renderLocalizedPages({ root, htmlRoot: html });
console.log("FRONTEND_BUILD=PASS");''',
)

# Dist checker includes localized pages, verifies assets/config representation, and bounds their HTML size.
replace_once(
    "scripts/check-frontend-dist.mjs",
    '''const indexHtml = await readFile(resolve(htmlRoot, "index.html"), "utf8");
const smartHtml = await readFile(resolve(htmlRoot, "smarthome.html"), "utf8");
for (const [name, text] of [["index", indexHtml], ["smarthome", smartHtml]]) {''',
    '''const indexHtml = await readFile(resolve(htmlRoot, "index.html"), "utf8");
const smartHtml = await readFile(resolve(htmlRoot, "smarthome.html"), "utf8");
const localizedHtml = Object.fromEntries(await Promise.all(
  ["en", "de", "lv"].map(async (language) => [
    language,
    await readFile(resolve(htmlRoot, language, "index.html"), "utf8")
  ])
));
for (const [name, text] of [["index", indexHtml], ["smarthome", smartHtml], ...Object.entries(localizedHtml)]) {''',
)
replace_once(
    "scripts/check-frontend-dist.mjs",
    '''assert.ok(
  indexHtml.includes(`src="/${indexEntry.file}?cfg=${nginxRepresentation}"`),
  "index HTML app representation is not bound to nginx.conf"
);
assert.ok(smartHtml.includes(`/${smartEntry.file}`), "Smart Home HTML does not reference manifest entry");''',
    '''assert.ok(
  indexHtml.includes(`src="/${indexEntry.file}?cfg=${nginxRepresentation}"`),
  "index HTML app representation is not bound to nginx.conf"
);
for (const [language, text] of Object.entries(localizedHtml)) {
  assert.ok(
    text.includes(`src="/${indexEntry.file}?cfg=${nginxRepresentation}"`),
    `${language} HTML app representation is not bound to nginx.conf`
  );
}
assert.ok(smartHtml.includes(`/${smartEntry.file}`), "Smart Home HTML does not reference manifest entry");''',
)
replace_once(
    "scripts/check-frontend-dist.mjs",
    '''  "frontend/styles/print.css"
]) {''',
    '''  "frontend/styles/print.css",
  "scripts/localize-frontend.mjs"
]) {''',
)
replace_once(
    "scripts/check-frontend-dist.mjs",
    '''  indexHtml: [(await stat(resolve(htmlRoot, "index.html"))).size, 21_000],
  smartHomeHtml: [(await stat(resolve(htmlRoot, "smarthome.html"))).size, 5_000]
};''',
    '''  indexHtml: [(await stat(resolve(htmlRoot, "index.html"))).size, 21_000],
  englishHtml: [(await stat(resolve(htmlRoot, "en", "index.html"))).size, 32_000],
  germanHtml: [(await stat(resolve(htmlRoot, "de", "index.html"))).size, 32_000],
  latvianHtml: [(await stat(resolve(htmlRoot, "lv", "index.html"))).size, 32_000],
  smartHomeHtml: [(await stat(resolve(htmlRoot, "smarthome.html"))).size, 5_000]
};''',
)

# CI deterministic identity, syntax checks and real nginx routes include localized output.
replace_once(
    ".github/workflows/ci.yml",
    '''            printf '%s\\0' html/index.html html/smarthome.html frontend-dist-manifest.json
          } | sort -z | xargs -0 sha256sum > "$first"''',
    '''            printf '%s\\0' html/index.html html/en/index.html html/de/index.html html/lv/index.html html/sitemap.xml html/smarthome.html frontend-dist-manifest.json
          } | sort -z | xargs -0 sha256sum > "$first"''',
)
replace_once(
    ".github/workflows/ci.yml",
    '''            printf '%s\\0' html/index.html html/smarthome.html frontend-dist-manifest.json
          } | sort -z | xargs -0 sha256sum > "$second"''',
    '''            printf '%s\\0' html/index.html html/en/index.html html/de/index.html html/lv/index.html html/sitemap.xml html/smarthome.html frontend-dist-manifest.json
          } | sort -z | xargs -0 sha256sum > "$second"''',
)
replace_once(
    ".github/workflows/ci.yml",
    '''            html/assets html/i18n html/index.html html/smarthome.html''',
    '''            html/assets html/i18n html/index.html html/en html/de html/lv html/sitemap.xml html/smarthome.html''',
)
replace_once(
    ".github/workflows/ci.yml",
    '''          node --check scripts/build-frontend.mjs
          node --check scripts/check-frontend-dist.mjs''',
    '''          node --check scripts/build-frontend.mjs
          node --check scripts/localize-frontend.mjs
          node --check scripts/check-frontend-dist.mjs''',
)
replace_once(
    ".github/workflows/ci.yml",
    '''          curl --fail --silent --show-error --head \\
            http://127.0.0.1:18088/favicon.svg >/dev/null''',
    '''          for language in en de lv; do
            body="$(curl --fail --silent --show-error "http://127.0.0.1:18088/${language}/")"
            grep -Fq "<html lang=\\"${language}\\">" <<<"$body"
            grep -Fq "<link rel=\\"canonical\\" href=\\"https://rozkalns.net/${language}/\\">" <<<"$body"
          done

          curl --fail --silent --show-error --head \\
            http://127.0.0.1:18088/favicon.svg >/dev/null''',
)

# Browser fixture understands directory index pages. Main CV language controls now navigate URLs.
replace_once(
    "tests/browser-smoke.mjs",
    '''function safeStaticPath(pathname) {
  const decoded = decodeURIComponent(pathname === "/" ? "/index.html" : pathname);''',
    '''function safeStaticPath(pathname) {
  const routed = pathname.endsWith("/") ? `${pathname}index.html` : pathname;
  const decoded = decodeURIComponent(routed);''',
)
text = read("tests/browser-smoke.mjs")
text = text.replace('await cdp.navigate(`${baseUrl}/`);', 'await cdp.navigate(`${baseUrl}/en/`);', 1)
old_state = '''      buttons: [...document.querySelectorAll('.language-switcher [data-lang]')].map((button) => ({
        language: button.dataset.lang,
        label: button.getAttribute('aria-label'),
        pressed: button.getAttribute('aria-pressed')
      })),'''
new_state = '''      controls: [...document.querySelectorAll('.language-switcher [data-lang]')].map((control) => ({
        language: control.dataset.lang,
        label: control.getAttribute('aria-label'),
        href: control.getAttribute('href'),
        current: control.getAttribute('aria-current')
      })),'''
if text.count(old_state) != 1:
    raise SystemExit("browser-smoke: initial language state mismatch")
text = text.replace(old_state, new_state, 1)
old_expect = '''    assert.deepEqual(initialLanguageState.buttons, [
      { language: "en", label: "English", pressed: "true" },
      { language: "de", label: "Deutsch", pressed: "false" },
      { language: "lv", label: "Latviešu", pressed: "false" }
    ]);'''
new_expect = '''    assert.deepEqual(initialLanguageState.controls, [
      { language: "en", label: "English", href: "/en/", current: "page" },
      { language: "de", label: "Deutsch", href: "/de/", current: null },
      { language: "lv", label: "Latviešu", href: "/lv/", current: null }
    ]);'''
if text.count(old_expect) != 1:
    raise SystemExit("browser-smoke: initial language expectation mismatch")
text = text.replace(old_expect, new_expect, 1)
old_de = '''    await cdp.evaluate(`document.querySelector('[data-lang="de"]').click()`);
    await cdp.waitFor(
      `document.documentElement.lang === "de" && document.querySelector('#profileLocation')?.textContent === "Dortmund, Deutschland"`,
      10_000,
      "German location localization"
    );'''
new_de = '''    const germanLoaded = cdp.waitForEvent("Page.loadEventFired", 15_000);
    await cdp.evaluate(`document.querySelector('[data-lang="de"]').click()`);
    await germanLoaded;
    await cdp.waitFor(
      `location.pathname === "/de/" && document.documentElement.lang === "de" && document.querySelector('#profileLocation')?.textContent === "Dortmund, Deutschland"`,
      10_000,
      "German localized URL"
    );'''
if text.count(old_de) != 1:
    raise SystemExit("browser-smoke: German switch mismatch")
text = text.replace(old_de, new_de, 1)
old_lv = '''    await cdp.evaluate(`document.querySelector('[data-lang="lv"]').click()`);
    await cdp.waitFor(
      `document.documentElement.lang === "lv" && document.title === "Andris Rožkalns · DevOps un Linux inženieris" && document.querySelector('#pdfLink')?.getAttribute('href') === "/cv-lv.pdf"`,
      10_000,
      "Latvian language switch"
    );'''
new_lv = '''    const latvianLoaded = cdp.waitForEvent("Page.loadEventFired", 15_000);
    await cdp.evaluate(`document.querySelector('[data-lang="lv"]').click()`);
    await latvianLoaded;
    await cdp.waitFor(
      `location.pathname === "/lv/" && document.documentElement.lang === "lv" && document.title === "Andris Rožkalns · DevOps un Linux inženieris" && document.querySelector('#pdfLink')?.getAttribute('href') === "/cv-lv.pdf"`,
      10_000,
      "Latvian localized URL"
    );'''
if text.count(old_lv) != 1:
    raise SystemExit("browser-smoke: Latvian switch mismatch")
text = text.replace(old_lv, new_lv, 1)
old_pressed = '''      await cdp.evaluate(`[...document.querySelectorAll('.language-switcher [data-lang]')].map((button) => [button.dataset.lang, button.getAttribute('aria-pressed')])`),
      [["en", "false"], ["de", "false"], ["lv", "true"]]'''
new_pressed = '''      await cdp.evaluate(`[...document.querySelectorAll('.language-switcher [data-lang]')].map((control) => [control.dataset.lang, control.getAttribute('aria-current')])`),
      [["en", null], ["de", null], ["lv", "page"]]'''
if text.count(old_pressed) != 1:
    raise SystemExit("browser-smoke: localized current-state mismatch")
text = text.replace(old_pressed, new_pressed, 1)
# Subsequent main-page navigations must stay on the current localized URL.
text = text.replace('await cdp.navigate(`${baseUrl}/`);', 'await cdp.navigate(`${baseUrl}/lv/`);')
text = text.replace("'.language-switcher button, .actions .button, #contactReveal, #chatLauncher'", "'.language-switcher [data-lang], .actions .button, #contactReveal, #chatLauncher'")
write("tests/browser-smoke.mjs", text)

# Existing source/generated contract now expects link-current semantics on main CV.
replace_once(
    "tests/test_frontend_contract.py",
    '''            'aria-busy="false"', 'aria-pressed="true"',''',
    '''            'aria-busy="false"', 'aria-current="page"',''',
)

# SEO contract: root is a canonical alias of /en/; real locale pages self-canonicalize.
seo = '''from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
ALTERNATES = {
    "en": "https://rozkalns.net/en/",
    "de": "https://rozkalns.net/de/",
    "lv": "https://rozkalns.net/lv/",
    "x-default": "https://rozkalns.net/en/",
}


class SeoCanonicalContractTest(unittest.TestCase):
    def test_root_alias_canonicalizes_to_english_locale(self):
        for relative in ("frontend/index.html", "html/index.html"):
            html = (ROOT / relative).read_text(encoding="utf-8")
            self.assertEqual(
                html.count('<link rel="canonical" href="https://rozkalns.net/en/">'),
                1,
                relative,
            )
            self.assertEqual(
                html.count('<meta property="og:url" content="https://rozkalns.net/en/">'),
                1,
                relative,
            )
            for language, href in ALTERNATES.items():
                marker = f'<link rel="alternate" hreflang="{language}" href="{href}">'
                self.assertEqual(html.count(marker), 1, f"{relative}: {marker}")

    def test_localized_pages_self_canonicalize_and_publish_reciprocal_hreflang(self):
        for language in ("en", "de", "lv"):
            html = (ROOT / f"html/{language}/index.html").read_text(encoding="utf-8")
            self.assertIn(f'<html lang="{language}">', html)
            self.assertEqual(
                html.count(f'<link rel="canonical" href="https://rozkalns.net/{language}/">'),
                1,
            )
            self.assertEqual(
                html.count(f'<meta property="og:url" content="https://rozkalns.net/{language}/">'),
                1,
            )
            for alternate, href in ALTERNATES.items():
                self.assertEqual(
                    html.count(f'<link rel="alternate" hreflang="{alternate}" href="{href}">'),
                    1,
                )
            self.assertIn(f'href="/{language}/" data-lang="{language}"', html)
            self.assertIn(f'data-lang="{language}" aria-label=', html)

    def test_preview_image_is_crawlable(self):
        robots = (ROOT / "html/robots.txt").read_text(encoding="utf-8")
        self.assertIn("User-agent: *", robots)
        self.assertIn("Allow: /", robots)
        self.assertNotIn("Disallow: /photo.jpg", robots)


if __name__ == "__main__":
    unittest.main()
'''
write("tests/test_seo_canonical.py", seo)

# Structured data preserves Person identity while ProfilePage URL follows each canonical locale.
person = '''import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_RE = re.compile(r'<script type="application/ld\\+json">\\s*(.*?)\\s*</script>', re.DOTALL)


def load_profile_page(relative):
    html = (ROOT / relative).read_text(encoding="utf-8")
    matches = SCRIPT_RE.findall(html)
    if len(matches) != 1:
        raise AssertionError(f"{relative}: expected exactly one JSON-LD script, got {len(matches)}")
    return json.loads(matches[0])


class ProfilePageStructuredDataContractTest(unittest.TestCase):
    def assert_privacy_boundary(self, profile):
        serialized = json.dumps(profile, sort_keys=True)
        for forbidden in ("telephone", "streetAddress", "postalCode", "birthDate", "spouse", "children", "familyName"):
            self.assertNotIn(f'"{forbidden}"', serialized)

    def test_root_alias_uses_english_canonical_profile_identity(self):
        for relative in ("frontend/index.html", "html/index.html"):
            profile = load_profile_page(relative)
            self.assertEqual(profile["@context"], "https://schema.org")
            self.assertEqual(profile["@type"], "ProfilePage")
            self.assertEqual(profile["@id"], "https://rozkalns.net/en/#profile")
            self.assertEqual(profile["url"], "https://rozkalns.net/en/")
            person = profile["mainEntity"]
            self.assertEqual(person["@id"], "https://rozkalns.net/#person")
            self.assertEqual(person["url"], "https://rozkalns.net/en/")
            self.assertEqual(person["name"], "Andris Rožkalns")
            self.assertEqual(person["image"], "https://rozkalns.net/photo.jpg")
            self.assertEqual(person["sameAs"], ["https://github.com/rozkalnsandris"])
            self.assert_privacy_boundary(profile)

    def test_localized_profile_pages_match_visible_locale(self):
        expected_roles = {
            "en": "Junior DevOps & Linux Engineer",
            "de": "Junior DevOps- & Linux-Engineer",
            "lv": "Junior DevOps un Linux inženieris",
        }
        for language, role in expected_roles.items():
            profile = load_profile_page(f"html/{language}/index.html")
            self.assertEqual(profile["@id"], f"https://rozkalns.net/{language}/#profile")
            self.assertEqual(profile["url"], f"https://rozkalns.net/{language}/")
            person = profile["mainEntity"]
            self.assertEqual(person["@id"], "https://rozkalns.net/#person")
            self.assertEqual(person["url"], "https://rozkalns.net/en/")
            self.assertEqual(person["jobTitle"], role)
            self.assertIn("Dortmund", person["description"])
            address = person["homeLocation"]["address"]
            self.assertEqual(address["addressLocality"], "Dortmund")
            self.assertEqual(address["addressCountry"], "DE")
            self.assertEqual([item["alternateName"] for item in person["knowsLanguage"]], ["lv", "en", "de"])
            self.assert_privacy_boundary(profile)


if __name__ == "__main__":
    unittest.main()
'''
write("tests/test_person_structured_data.py", person)

# Sitemap includes only canonical localized URLs and a complete reciprocal xhtml alternate matrix.
sitemap = '''import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITEMAP = ROOT / "html" / "sitemap.xml"
ROBOTS = ROOT / "html" / "robots.txt"
SMARTHOME = ROOT / "html" / "smarthome.html"
NS = {
    "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
    "xhtml": "http://www.w3.org/1999/xhtml",
}
EXPECTED = {
    "en": "https://rozkalns.net/en/",
    "de": "https://rozkalns.net/de/",
    "lv": "https://rozkalns.net/lv/",
    "x-default": "https://rozkalns.net/en/",
}


class SitemapContractTests(unittest.TestCase):
    def test_sitemap_contains_canonical_locales_with_reciprocal_alternates(self):
        root = ET.parse(SITEMAP).getroot()
        self.assertEqual(root.tag, f"{{{NS['sm']}}}urlset")
        urls = root.findall("sm:url", NS)
        self.assertEqual(
            [url.find("sm:loc", NS).text for url in urls],
            [EXPECTED["en"], EXPECTED["de"], EXPECTED["lv"]],
        )
        for url in urls:
            alternates = {
                link.attrib["hreflang"]: link.attrib["href"]
                for link in url.findall("xhtml:link", NS)
            }
            self.assertEqual(alternates, EXPECTED)
        xml = SITEMAP.read_text(encoding="utf-8")
        self.assertNotIn("<loc>https://rozkalns.net/</loc>", xml)
        self.assertNotIn("<priority>", xml)
        self.assertNotIn("<changefreq>", xml)
        self.assertNotIn("<lastmod>", xml)

    def test_robots_advertises_sitemap_and_noindex_demo_stays_excluded(self):
        robots = ROBOTS.read_text(encoding="utf-8").splitlines()
        self.assertEqual(
            [line for line in robots if line.lower().startswith("sitemap:")],
            ["Sitemap: https://rozkalns.net/sitemap.xml"],
        )
        smarthome = SMARTHOME.read_text(encoding="utf-8")
        self.assertIn('<meta name="robots" content="noindex">', smarthome)
        self.assertNotIn("smarthome.html", SITEMAP.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
'''
write("tests/test_sitemap_contract.py", sitemap)

# Static file assertions prove each locale is translated before JavaScript executes.
localized = '''import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "en": ("Junior DevOps &amp; Linux Engineer", "Dortmund, Germany", "/cv.pdf"),
    "de": ("Junior DevOps- &amp; Linux-Engineer", "Dortmund, Deutschland", "/cv-de.pdf"),
    "lv": ("Junior DevOps un Linux inženieris", "Dortmund, Vācija", "/cv-lv.pdf"),
}


class LocalizedPageContractTests(unittest.TestCase):
    def test_localized_html_is_pretranslated_before_javascript(self):
        for language, (role, location, pdf) in EXPECTED.items():
            html = (ROOT / f"html/{language}/index.html").read_text(encoding="utf-8")
            self.assertIn(f'<html lang="{language}">', html)
            self.assertIn(f'data-i18n="role">{role}</p>', html)
            self.assertRegex(html, rf'id="profileLocation"[^>]*>{re.escape(location)}</span>')
            self.assertRegex(html, rf'id="pdfLink" href="{re.escape(pdf)}"')
            self.assertIn(f'data-lang="{language}" aria-label=', html)
            current = re.findall(r'<a[^>]+data-lang="([^"]+)"[^>]+aria-current="page"', html)
            self.assertEqual(current, [language])

    def test_root_alias_is_english_but_not_a_sitemap_canonical(self):
        root_html = (ROOT / "html/index.html").read_text(encoding="utf-8")
        self.assertIn('<html lang="en">', root_html)
        self.assertIn('<link rel="canonical" href="https://rozkalns.net/en/">', root_html)
        sitemap = (ROOT / "html/sitemap.xml").read_text(encoding="utf-8")
        self.assertNotIn("<loc>https://rozkalns.net/</loc>", sitemap)

    def test_translation_documents_remain_single_source_of_visible_copy(self):
        for language in EXPECTED:
            messages = json.loads((ROOT / f"content/translations/{language}.json").read_text(encoding="utf-8"))
            html = (ROOT / f"html/{language}/index.html").read_text(encoding="utf-8")
            self.assertIn(messages["tagline"].replace("&", "&amp;"), html)
            self.assertIn(messages["about_p1"].replace("&", "&amp;"), html)


if __name__ == "__main__":
    unittest.main()
'''
write("tests/test_localized_pages.py", localized)

# Basic source-level syntax sanity for the localization renderer itself.
renderer = read("scripts/localize-frontend.mjs")
if 'LOCALIZED_LANGUAGES = Object.freeze(["en", "de", "lv"])' not in renderer:
    raise SystemExit("localized renderer language set missing")
