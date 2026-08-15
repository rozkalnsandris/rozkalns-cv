from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    file = ROOT / path
    text = file.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"{path}: expected one match")
    file.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once(
    "frontend/index.html",
    '''      <nav class="language-switcher" data-i18n-label="profile_languages_label" aria-label="Language">
        <a href="/en/" data-lang="en" aria-label="English" aria-current="page">EN</a>
        <a href="/de/" data-lang="de" aria-label="Deutsch">DE</a>
        <a href="/lv/" data-lang="lv" aria-label="Latviešu">LV</a>
      </nav>''',
    '''      <div class="language-switcher" role="group" data-i18n-label="profile_languages_label" aria-label="Language">
        <a href="/en/" data-lang="en" aria-label="English" aria-current="page">EN</a>
        <a href="/de/" data-lang="de" aria-label="Deutsch">DE</a>
        <a href="/lv/" data-lang="lv" aria-label="Latviešu">LV</a>
      </div>''',
)

path = ROOT / "tests/test_html_semantics.py"
text = path.read_text(encoding="utf-8")
old = '''    def test_language_switchers_are_named_toggle_groups(self) -> None:
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
'''
new = '''    def test_language_switchers_are_named_and_stateful(self) -> None:
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
            controls = [row for row in parsed.elements if row.attrs.get("data-lang")]
            self.assertEqual({row.attrs.get("data-lang") for row in controls}, set(expected_labels))
            self.assertEqual(
                {row.attrs.get("data-lang"): row.attrs.get("aria-label") for row in controls},
                expected_labels,
            )
            if path.name == "smarthome.html":
                pressed = [row for row in controls if row.attrs.get("aria-pressed") == "true"]
                self.assertEqual(len(pressed), 1)
                self.assertTrue(all(row.tag == "button" for row in controls))
                self.assertTrue(all(row.attrs.get("aria-pressed") in {"true", "false"} for row in controls))
            else:
                self.assertTrue(all(row.tag == "a" for row in controls))
                self.assertEqual(
                    {row.attrs.get("data-lang"): row.attrs.get("href") for row in controls},
                    {"en": "/en/", "de": "/de/", "lv": "/lv/"},
                )
                current = [row for row in controls if row.attrs.get("aria-current") == "page"]
                self.assertEqual([row.attrs.get("data-lang") for row in current], ["en"])
                self.assertTrue(all("aria-pressed" not in row.attrs for row in controls))
'''
if text.count(old) != 1:
    raise SystemExit("tests/test_html_semantics.py: legacy language switcher test missing")
path.write_text(text.replace(old, new, 1), encoding="utf-8")

path = ROOT / "tests/test_main_document_title.py"
text = path.read_text(encoding="utf-8")
old = '''    def test_main_title_updates_on_every_successful_language_apply(self) -> None:
        source = (ROOT / "frontend" / "app.mjs").read_text(encoding="utf-8")
        self.assertIn("export function updateMainDocumentTitle({ messages }", source)
        self.assertIn("const role = messages?.role;", source)
        self.assertIn('role.startsWith("Junior ")', source)
        self.assertIn('documentLike.title = `Andris Rožkalns · ${titleRole}`;', source)
        self.assertIn(
            "createLanguageController({ pdfs: PDFS, onApplied: updateMainDocumentTitle })",
            source,
        )
'''
new = '''    def test_main_title_uses_url_owned_initial_language_apply(self) -> None:
        source = (ROOT / "frontend" / "app.mjs").read_text(encoding="utf-8")
        self.assertIn("export function updateMainDocumentTitle({ messages }", source)
        self.assertIn("const role = messages?.role;", source)
        self.assertIn('role.startsWith("Junior ")', source)
        self.assertIn('documentLike.title = `Andris Rožkalns · ${titleRole}`;', source)
        self.assertIn("onApplied: updateMainDocumentTitle,", source)
        self.assertIn("initialLanguage: document.documentElement.lang", source)
        self.assertIn("await languageController.tryApply(languageController.language);", source)
'''
if text.count(old) != 1:
    raise SystemExit("tests/test_main_document_title.py: legacy title contract missing")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
