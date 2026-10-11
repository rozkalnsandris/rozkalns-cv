"""Regression for the three featured project link destinations (#518)."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
GITHUB_CASE = "https://github.com/rozkalnsandris/rozkalns-cv/blob/main/docs/TROUBLESHOOTING_CASE_STUDY.md"
KEYS = ("v2_lab_link", "v2_homelab_link", "v2_cv_link_github")
ACTION = re.compile(
    r'<div class="project-actions"><a ([^>]+)><span data-ui-i18n="([^"]+)">([^<]+)</span> <span aria-hidden="true">([^<]+)</span></a></div>'
)


class ProjectActionDestinationsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.copy = json.loads((ROOT / "content/ui-v2.json").read_text(encoding="utf-8"))["i18n"]

    def check_actions(self, document, language):
        actions = ACTION.findall(document)
        self.assertEqual(len(actions), 3)
        self.assertEqual(tuple(row[1] for row in actions), KEYS)
        self.assertEqual(tuple(row[2] for row in actions), tuple(self.copy[language][key] for key in KEYS))
        self.assertEqual(len({row[2] for row in actions}), 3)
        self.assertIn(f'href="/{language}/lab/" data-local-route="lab/"', actions[0][0])
        self.assertIn(f'href="/{language}/proof/#homelab" data-local-route="proof/#homelab"', actions[1][0])
        self.assertIn(f'href="{GITHUB_CASE}" rel="external"', actions[2][0])
        self.assertEqual(tuple(row[3] for row in actions), ("→", "→", "↗"))
        self.assertNotIn('target="_blank"', actions[2][0])

    def test_source_labels(self):
        self.check_actions((ROOT / "frontend/index.html").read_text(encoding="utf-8"), "en")

    def test_localized_no_js_routes_and_deep_links(self):
        self.assertTrue((ROOT / "docs/TROUBLESHOOTING_CASE_STUDY.md").is_file())
        for language in ("en", "de", "lv"):
            with self.subTest(language=language):
                page = (ROOT / "html" / language / "index.html").read_text(encoding="utf-8")
                self.check_actions(page, language)
                self.assertTrue((ROOT / "html" / language / "lab" / "index.html").is_file())
                proof = (ROOT / "html" / language / "proof" / "index.html").read_text(encoding="utf-8")
                self.assertIn('id="homelab" data-proof-project-id="homelab"', proof)


if __name__ == "__main__":
    unittest.main()
