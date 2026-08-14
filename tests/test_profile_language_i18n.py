from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]

EXPECTED = {
    "en": {
        "profile_languages_label": "Languages",
        "profile_lang_latvian": "Latvian",
        "profile_lang_english": "English",
        "profile_lang_german": "German",
        "profile_level_native": "native",
        "profile_level_fluent": "fluent",
    },
    "de": {
        "profile_languages_label": "Sprachen",
        "profile_lang_latvian": "Lettisch",
        "profile_lang_english": "Englisch",
        "profile_lang_german": "Deutsch",
        "profile_level_native": "Muttersprache",
        "profile_level_fluent": "fließend",
    },
    "lv": {
        "profile_languages_label": "Valodas",
        "profile_lang_latvian": "Latviešu",
        "profile_lang_english": "Angļu",
        "profile_lang_german": "Vācu",
        "profile_level_native": "dzimtā valoda",
        "profile_level_fluent": "brīvi",
    },
}


class ProfileLanguageI18nTests(unittest.TestCase):
    def test_profile_language_row_uses_canonical_i18n_bindings(self) -> None:
        html = (ROOT / "frontend/index.html").read_text(encoding="utf-8")

        self.assertIn(
            'class="profile-languages" role="list" data-i18n-label="profile_languages_label"',
            html,
        )
        for key in (
            "profile_lang_latvian",
            "profile_lang_english",
            "profile_lang_german",
            "profile_level_native",
            "profile_level_fluent",
        ):
            self.assertIn(f'data-i18n="{key}"', html)

        self.assertIn("<small>B1</small>", html)

    def test_profile_language_translations_are_complete(self) -> None:
        for language, expected in EXPECTED.items():
            path = ROOT / "content" / "translations" / f"{language}.json"
            messages = json.loads(path.read_text(encoding="utf-8"))
            for key, value in expected.items():
                self.assertEqual(messages[key], value, f"{language}:{key}")


if __name__ == "__main__":
    unittest.main()
