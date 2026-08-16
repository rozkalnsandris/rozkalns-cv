from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class AccessibleLabelI18nTests(unittest.TestCase):
    def test_main_accessibility_regions_use_valid_naming_semantics(self) -> None:
        html = (ROOT / "frontend/index.html").read_text(encoding="utf-8")
        self.assertIn('<img class="profile-photo" src="./photo.webp" alt="" width="118" height="118">', html)
        self.assertIn("<h1>Andris Rožkalns</h1>", html)
        self.assertIn(
            'class="language-switcher" role="group" data-i18n-label="profile_languages_label" aria-label="Language"',
            html,
        )
        self.assertNotIn('class="focus-tags"', html)
        self.assertIn('<nav class="site-nav" aria-label="CV">', html)
        self.assertIn(
            'class="profile-languages" role="list" data-i18n-label="profile_languages_label" aria-label="Languages"',
            html,
        )
        self.assertEqual(html.count('class="profile-language" role="listitem"'), 3)

    def test_smarthome_language_group_uses_canonical_translation(self) -> None:
        html = (ROOT / "frontend/smarthome.html").read_text(encoding="utf-8")
        self.assertIn(
            'class="language-switcher" role="group" data-i18n-label="profile_languages_label" aria-label="Language"',
            html,
        )

    def test_language_group_reuses_complete_canonical_translation(self) -> None:
        expected = {"en": "Languages", "de": "Sprachen", "lv": "Valodas"}
        for language, value in expected.items():
            messages = json.loads(
                (ROOT / "content" / "translations" / f"{language}.json").read_text(encoding="utf-8")
            )
            self.assertEqual(messages["profile_languages_label"], value, language)

if __name__ == "__main__":
    unittest.main()
