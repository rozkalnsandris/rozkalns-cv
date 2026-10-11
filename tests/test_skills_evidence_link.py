"""Regression for localized skill-level evidence links (#519), including no-JS HTML."""

import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
KEY = "v2_skill_proof_link"
LINK = re.compile(
    r'<section id="skills"><div class="section-heading">'
    r'<h2 data-i18n="skills_title">[^<]+</h2>'
    r'<a class="section-link" href="([^"]+)" data-local-route="proof/" '
    r'data-ui-i18n="v2_skill_proof_link">([^<]+)</a></div>'
)


class SkillsEvidenceLinkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.labels = json.loads((ROOT / "content/ui-v2.json").read_text(encoding="utf-8"))["i18n"]

    def assert_link(self, file, language):
        markup = file.read_text(encoding="utf-8")
        links = LINK.findall(markup)
        self.assertEqual(len(links), 1, file)
        self.assertEqual(links[0], (f"/{language}/proof/", self.labels[language][KEY]))
        self.assertTrue(self.labels[language][KEY].strip())
        self.assertEqual(markup.count(f'data-ui-i18n="{KEY}"'), 1)

    def test_source_and_default_entry_link(self):
        self.assert_link(ROOT / "frontend/index.html", "en")
        self.assert_link(ROOT / "html/index.html", "en")

    def test_localized_no_js_proof_destinations_and_existing_levels(self):
        taxonomy = json.loads((ROOT / "content/profile.json").read_text(encoding="utf-8"))["skills"]
        for language in ("en", "de", "lv"):
            with self.subTest(language=language):
                self.assert_link(ROOT / "html" / language / "index.html", language)
                proof = (ROOT / "html" / language / "proof" / "index.html").read_text(encoding="utf-8")
                self.assertIn('class="proof-skills"', proof)
                levels = re.findall(r'data-proof-level="([^"]+)"', proof)
                self.assertTrue(levels)
                self.assertTrue(set(levels).issubset(set(taxonomy)), levels)

    def test_source_copy_retains_existing_scope(self):
        source = (ROOT / "frontend/index.html").read_text(encoding="utf-8")
        start = source.index('<section id="skills">')
        end = source.index('</section>', start)
        skills = source[start:end]
        self.assertIn('data-ui-i18n="v2_skill_scope"', skills)
        self.assertNotIn("progressbar", skills)


if __name__ == "__main__":
    unittest.main()
